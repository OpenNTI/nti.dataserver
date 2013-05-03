# -*- coding: utf-8 -*-
"""
WebVTT parser.

https://github.com/humphd/node-webvtt/blob/master/lib/parser.js

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import re
import six
import time
from cStringIO import StringIO

class Cue(object):

	def __init__(self, id_=u"", text=u"", tree=None, start_time=0, end_time=0, size=0, pause_on_exit=False,
				 direction=u"horizontal", snap_to_lines=True, line_position=u"auto", text_position=0, alignment=u"middle"):

		self.id = id_
		self.size = size
		self.text = text
		self.tree = tree
		self.end_time = end_time
		self.direction = direction
		self.start_time = start_time
		self.alignment = alignment
		self.pause_on_exit = pause_on_exit
		self.snap_to_lines = snap_to_lines
		self.line_position = line_position
		self.text_position = text_position

# ----------------------------------

class _WebVTTCueTimingsAndSettingsParser():

	SPACE = r'[\u0020\t\f]'
	NOSPACE = r'[^\u0020\t\f]'

	def __init__(self, line, error_handler):
		self.pos = 0
		self.line = line
		self.space_before_setting = True
		self.err = lambda message: error_handler(message, self.pos + 1)

	def skip(self, pattern):
		while self.pos < len(self.line) and re.match(pattern, self.line[self.pos]):
			self.pos += 1

	def collect(self, pattern):
		s = []
		while self.pos < len(self.line) and re.match(pattern, self.line[self.pos]):
			s.append(self.line[self.pos])
			self.pos += 1
		return ''.join(s)

	def timestamp(self):
		"""
		http://dev.w3.org/html5/webvtt/#collect-a-webvtt-timestamp
		"""
		units = "minutes"

		# 3
		if self.pos >= len(self.line):
			self.err("No timestamp found.")
			return None

		# 4
		if not re.match('\d', self.line[self.pos]):
			self.err("Timestamp must start with a character in the range 0-9.")
			return None

		# 5-7
		val1 = self.collect(r'\d')
		if len(val1) > 2 or int(val1, 10) > 59:
			units = "hours"

		# 8
		if self.pos >= len(self.line) or self.line[self.pos] != ':':
			self.err("No time unit separator found.")
			return None

		self.pos += 1

		# 9-11
		val2 = self.collect(r'\d')
		if len(val2) != 2:
			self.err("Must be exactly two digits.")
			return None

		# 12
		if units == "hours" or self.line[self.pos] == ":":
			if self.line[self.pos] != ":":
				self.err("No seconds found or minutes is greater than 59.")
				return None
			self.pos += 1
			val3 = self.collect(r'\d')
			if len(val3) != 2:
				self.err("Must be exactly two digits.")
				return None
		else:
			val3 = val2
			val2 = val1
			val1 = "0"

		# 13
		if self.pos >= len(self.line) or self.line[self.pos] != '.':
			self.err("No decimal separator (\".\") found.")
			return None

		self.pos += 1

		# 14-16
		val4 = self.collect(r'\d')
		if len(val4) != 3:
			self.err("Milliseconds must be given in three digits.")
			return None

		# 17
		if int(val2, 10) > 59:
			self.err("You cannot have more than 59 minutes.")
			return None

		if int(val3, 10) > 59:
			self.err("You cannot have more than 59 seconds.")
			return None

		return int(val1, 10) * 60 * 60 + int(val2, 10) * 60 + int(val3, 10) + int(val4, 10) / 1000

	def parse_settings(self, data, cue):
		"""
		http://dev.w3.org/html5/webvtt/#parse-the-webvtt-settings
		"""
		seen = set()
		settings = re.split(self.SPACE, data)
		for i in xrange(len(settings)):
			if settings[i] == "":
				continue
			index = settings[i].find(':')
			setting = settings[i][0:index]
			value = settings[i][index + 1:]

			if setting in seen:
				self.err("Duplicate setting.")
			seen.add(setting)

			if value == "":
				self.err("No value for setting defined.")
				return None

			if setting == "vertical":  # writing direction
				if value != "rl" and value != "lr":
					self.err("Writing direction can only be set to 'rl' or 'rl'.")
					continue
				cue.direction = value
			elif setting == "line":  # line position
				if not re.match(r'\d', value):
					self.err("Line position takes a number or percentage.")
					continue

				if value.find("-", 1) != -1:
					self.err("Line position can only have '-' at the start.")
					continue

				if value.find("%") != -1 and value.find("%") != len(value) - 1:
					self.err("Line position can only have '%' at the end.")
					continue

				if value[0] == "-" and value[-1] == "%":
					self.err("Line position cannot be a negative percentage.")
					continue

				if value[-1] == "%":
					if int(value, 10) > 100:
						self.err("Line position cannot be >100%.")
						continue
					cue['snap_to_lines'] = False
				cue.line_position = int(value, 10)
			elif setting == "position":  # text position
				if value[-1] != "%":
					self.err("Text position must be a percentage.")
					continue

				if int(value, 10) > 100:
					self.err("Size cannot be >100%.")
					continue

				cue.text_position = int(value, 10)
			elif setting == "size":  # size
				if value[-1] != "%":
					self.err("Size must be a percentage.")
					continue

				if int(value, 10) > 100:
					self.err("Size cannot be >100%.")
					continue

				cue.size = int(value, 10)
			elif setting == "align":  # alignment
				if value != "start" and value != "middle" and value != "end":
					self.err("Alignment can only be set to 'start', 'middle', or 'end'.")
					continue
				cue.alignment = value
			else:
				self.err("Invalid setting.")

	def parse(self, cue, previous_cue_start):
		self.skip(self.SPACE)
		cue.start_time = self.timestamp()
		if cue.start_time is None:
			return None

		if cue.start_time < previous_cue_start:
			self.err("Start timestamp is not greater than or equal to start timestamp of previous cue.")

		if re.match(self.NOSPACE, self.line[self.pos]):
			self.err("Timestamp not separated from '-->' by whitespace.")

		self.skip(self.SPACE)

		# 6-8
		if self.line[self.pos] != "-":
			self.err("No valid timestamp separator found.")
			return None

		self.pos += 1
		if self.line[self.pos] != "-":
			self.err("No valid timestamp separator found.")
			return None

		self.pos += 1
		if self.line[self.pos] != ">":
			self.err("No valid timestamp separator found.")
			return None

		self.pos += 1
		if re.match(self.NOSPACE, self.line[self.pos]):
			self.err("'-->' not separated from timestamp by whitespace.")

		self.skip(self.SPACE)
		cue.end_time = self.timestamp()
		if cue.end_time is None:
			return None

		if cue.end_time <= cue.start_time:
			self.err("End timestamp is not greater than start timestamp.")

		if self.pos < len(self.line) and re.match(self.NOSPACE, self.line[self.pos]):
			self.space_before_setting = False

		self.skip(self.SPACE)
		self.parse_settings(self.line[self.pos:], cue)
		return True

	def parse_timestamp(self):
		ts = self.timestamp()
		if self.pos >= len(self.line):
			self.err("Timestamp must not have trailing characters.")
			return None
		return ts

# ----------------------------------

class _Result(object):

	def __init__(self, **kwargs):
		self.__dict__.update(**kwargs)

	def __getattr__(self, name):
		return self.__dict__.get(name, None)

class _WebVTTCueTextParser(object):

	def __init__(self, line, error_handler):
		self.pos = 0
		self.line = line
		self.err = lambda message: error_handler(message, self.pos + 1)

	def parse(self, cue_start, cue_end):
		timestamps = []
		result = current = _Result(children=[])

		def attach(token, current):
			current.children.append(_Result(type=u"object", name=token[1], classes=token[2], children=[], parent=current))
			current = current.children[-1]
			return current

		def in_scope(name):
			node = current
			while node:
				if node.name == name:
					return True
				node = node.parent
			return False

		while self.pos < len(self.line):
			token = self.next_token()
			if token[0] == "text":
				current.children.append(_Result(type=u"text", value=token[1], parent=current))
			elif token[0] == "start tag":
				name = token[1]
				if name != "v" and token[3] != "":
					self.err("Only <v> can have an annotation.")

				if name in ("c", "i", "b", "u", "ruby"):
					current = attach(token, current)
				elif name == "rt" and current.name == "ruby":
					current = attach(token, current)
				elif name == "v":
					if in_scope("v"):
						self.err("<v> cannot be nested inside itself.")
					current = attach(token, current)
					current.value = token[3]  # annotation
					if not token[3]:
						self.err("<v> requires an annotation.")
				else:
					self.err("Incorrect start tag.")
			elif token[0] == "end tag":
				# XXX check <ruby> content
				if token[1] == current.name:
					current = current.parent
				elif token[1] == "ruby" and current.name == "rt":
					current = current.parent.parent
				else:
					self.err("Incorrect end tag.")
			elif token[0] == "timestamp":
				timings = _WebVTTCueTimingsAndSettingsParser(token[1], self.err)
				timestamp = timings.parseTimestamp()
				if timestamp != None:
					if timestamp <= cue_start or timestamp >= cue_end:
						self.err("Timestamp tag must be between start timestamp and end timestamp.")
					if timestamps.length > 0 and timestamps[-1] >= timestamp:
						self.err("Timestamp tag must be greater than any previous timestamp tag.")

					current.children.push(_Result(type="timestamp", value=timestamp, parent=current))
					timestamps.push(timestamp)

		while current.parent:
			if current.name != "v":
				self.err("Required end tag missing.")
			current = current.parent
		return result

	def next_token(self):
		buff = ""
		result = ""
		classes = []
		state = "data"
		while self.pos <= len(self.line) or self.pos == 0:
			c = self.line[self.pos] if self.pos < len(self.line) else None
			if state == "data":
				if c == "&":
					buff = c
					state = "escape"
				elif c == "<" and result == "":
					state = "tag"
				elif c == "<" or c is None:
					return ["text", result]
				else:
					result += c
			elif state == "escape":
				if c == "&":
					# XXX is this non-conforming?
					result += buff
					buff = c
				elif c in "ampltg":
					buff += c
				elif c == ";":
					if buff == "&amp":
						result += "&"
					elif buff == "&lt":
						result += "<"
					elif buff == "&gt":
						result += ">"
					else:
						self.err("Incorrect escape.")
						result += buff + ";"
					state = "data"
				elif c == "<" or c == None:
					self.err("Incorrect escape.")
					result += buff
					return ["text", result]
				else:
					self.err("Incorrect escape.")
					result += buff + c
					state = "data"
			elif state == "tag":
				if c == "\t" or c == "\n" or c == "\f" or c == " ":
					state = "start tag annotation"
				elif c == ".":
					state = "start tag class"
				elif c == "/":
					state = "end tag"
				elif re.match('\d', c):
					result = c
					state = "timestamp tag"
				elif c == ">" or c == None:
					if c == ">":
						self.pos += 1
					return ["start tag", "", [], ""]
				else:
					result = c
					state = "start tag"
			elif state == "start tag":
				if c == "\t" or c == "\f" or c == " ":
					state = "start tag annotation"
				elif c == "\n":
					buff = c
					state = "start tag annotation"
				elif c == ".":
					state = "start tag class"
				elif c == ">" or c == None:
					if c == ">":
						self.pos += 1
					return ["start tag", result, [], ""]
				else:
					result += c
			elif state == "start tag class":
				if c == "\t" or c == "\f" or c == " ":
					classes.append(buff)
					buff = ""
					state = "start tag annotation"
				elif c == "\n":
					classes.append(buff)
					buff = c
					state = "start tag annotation"
				elif c == ".":
					classes.append(buff)
					buff = ""
				elif c == ">" or c == None:
					if c == ">":
						self.pos += 1
					classes.push(buff)
					return ["start tag", result, classes, ""]
				else:
					buff += c

			elif state == "start tag annotation":
				if c == ">" or c == None:
					if c == ">":
						self.pos += 1

					ts = filter(lambda x: True if x else False, re.split('[\u0020\t\f\r\n]+', buff))
					buff = " ".join(ts)
					return ["start tag", result, classes, buff]
				else:
					buff += c
			elif state == "end tag":
				if c == ">" or c == None:
					if c == ">":
						self.pos += 1
					return ["end tag", result]
				else:
					result += c
			elif state == "timestamp tag":
				if c == ">" or c == None:
					if c == ">":
						self.pos += 1
					return ["timestamp", result]
				else:
					result += c
			else:
				self.err("Never happens.")
			# 8
			self.pos += 1

# ----------------------------------

class WebVTTParser(object):

	NEWLINE = r'[\r\n|\r|\n]'

	def parse(self, source):

		cues = []
		errors = []
		linepos = 0
		start_time = time.time()

		def err(message, col=None):
			errors.append({'message':message, 'line':linepos + 1, 'col':col})

		already_collected = False
		source = StringIO(source) if isinstance(source, six.string_types) else source
		lines = [x.lstrip() for x in re.split(self.NEWLINE, source.read())]

		# SIGNATURE
		if 	len(lines[linepos]) < 6 or lines[linepos].index("WEBVTT") != 0 or \
			(len(lines[linepos]) > 6 and lines[linepos][6] != " " and lines[linepos][6] != "\t"):
			err("No valid signature. (File needs to start with \"WEBVTT\".)", linepos)

		linepos += 1

		# HEADER
		while linepos < len(lines) and lines[linepos] != "":
			err("No blank line after the signature.")
			if lines[linepos].index("-->") != -1:
				already_collected = True
				break
			linepos += 1

		# CUE LOOP
		while linepos < len(lines):

			# skip empty lines
			while linepos < len(lines) and not already_collected and lines[linepos] == "":
				linepos += 1

			# check EOF
			if not already_collected and linepos >= len(lines):
				break

			cue = Cue(id_="", start_time=0, end_time=0, pause_on_exit=False, direction=u"horizontal", snap_to_lines=True,
					  line_position=u"auto", text_position=50, size=100, alignment=u"middle", text=u"", tree=None)

			if lines[linepos].find("-->") == -1:
				cue.id = lines[linepos]
				linepos += 1
				if linepos >= len(lines[linepos]) or lines[linepos] == "":
					err("Cue identifier cannot be standalone.")
					continue

			# TIMINGS
			previous_cue_start = 0
			already_collected = False
			timings = _WebVTTCueTimingsAndSettingsParser(lines[linepos], err)
			if cues:
				previous_cue_start = cues[-1].start_time

			if not timings.parse(cue, previous_cue_start):
				# BAD CUE
				cue = None
				linepos += 1

				# BAD CUE LOOP
				while linepos < len(lines) and lines[linepos] != "":
					if lines[linepos].find("-->") != -1:
						already_collected = True
						break
					linepos += 1
				continue

			linepos += 1

			# CUE TEXT LOOP
			while linepos < len(lines) and lines[linepos] != "":
				if lines[linepos].find("-->") != -1:
					err("Blank line missing before cue.")
					already_collected = True
					break
				if cue.text != "":
					cue.text += "\n"
				cue.text += lines[linepos]
				linepos += 1

			# CUE TEXT PROCESSING
			cue_text_parser = _WebVTTCueTextParser(cue.text, err)
			cue.tree = cue_text_parser.parse(cue.start_time, cue.end_time)
			cues.append(cue)

		# SORT Cues
		def cue_sort(a, b):
			if a.start_time < b.start_time:
				return -1
			if a.start_time > b.start_time:
				return 1
			if a.end_time > b.end_time:
				return -1
			if a.end_time < b.end_time:
				return 1
			return 0
		cues = sorted(cues, cmp=cue_sort)

		result = {'cues':cues, 'errors':errors, 'time':time.time() - start_time}
		return result

if __name__ == '__main__':
	s = """WEBVTT

00:11.000 --> 00:13.000 vertical:rl
<v Roger Bingham>We are in New York City

00:13.000 --> 00:16.000
<v Roger Bingham>We're actually at the Lucern Hotel, just down the street

00:16.000 --> 00:18.000
<v Roger Bingham>from the American Museum of Natural History

00:18.000 --> 00:20.000
<v Roger Bingham>And with me is Neil deGrasse Tyson

00:20.000 --> 00:22.000
<v Roger Bingham>Astrophysicist, Director of the Hayden Planetarium
"""
	parser = WebVTTParser()
	parser.parse(s)
