# -*- coding: utf-8 -*-
"""
video transcript parsers.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import re
import six
from cStringIO import StringIO

from zope import interface

from . import VideoTranscript
from . import VideoTranscriptEntry
from . import interfaces as media_interfaces

class _YoutubeVideoTranscriptParser(object):

	timestamp_exp = r'[0-9]?[0-9]:[0-9]{2}:[0-9]{2}[,|\.][0-9]{3}'
	trx_times_exp = r'(%s)(,|\s+-->\s+)(%s)' % (timestamp_exp, timestamp_exp)
	trx_times_pattern = re.compile(trx_times_exp, re.U)

	@classmethod
	def fix_timestamp(cls, ts):
		ts = ts.replace(',', '.')
		splits = ts.split(':')
		if splits and len(splits[0]) == 1:
			ts = '0' + ts
		return ts

	@classmethod
	def is_valid_timestamp_range(cls, s):
		result = cls.trx_times_pattern.search(s)
		return result

	@classmethod
	def get_timestamp_range(cls, s):
		m = cls.trx_times_pattern.search(s)
		if m is not None:
			g = m.groups()
			start_time = cls.fix_timestamp(g[0])
			end_time = cls.fix_timestamp(g[2])
			return (start_time, end_time)
		else:
			return None

	@classmethod
	def _fix_source(cls, source):
		if isinstance(source, six.string_types):
			source = StringIO(source)
		return source

	@classmethod
	def _create_transcript_entry(cls, text, trange, eid=None):
		transcript = '\n'.join(text)
		e = VideoTranscriptEntry(id=eid,
								 transcript=transcript,
								 start_timestamp=trange[0],
								 end_timestamp=trange[1])
		return e

@interface.implementer(media_interfaces.ISRTVideoTranscriptParser)
class _SRTVideoTranscriptParser(_YoutubeVideoTranscriptParser):

	def parse(self, source):
		source = self._fix_source(source)
		eid = trange = text = None
		result = VideoTranscript()
		while True:
			line = source.readline()
			if not line or not line.strip():
				if range and text:
					e = self._create_transcript_entry(text, trange, eid)
					result.entries.append(e)
				eid = trange = text = None
				if not line:
					break
			else:
				line = unicode(line.rstrip())
				if not trange and line.isdigit() :
					eid = line
				elif not trange and self.is_valid_timestamp_range(line):
					trange = self.get_timestamp_range(line)
				else:
					text = [] if text is None else text
					text.append(line)
		return result

@interface.implementer(media_interfaces.ISBVVideoTranscriptParser)
class _SBVVideoTranscriptParser(_YoutubeVideoTranscriptParser):

	def parse(self, source):
		source = self._fix_source(source)
		trange = text = None
		result = VideoTranscript()
		while True:
			line = source.readline()
			if not line or not line.strip():
				if range and text:
					eid = unicode(len(result) + 1)
					e = self._create_transcript_entry(text, trange, eid)
					result.entries.append(e)
				trange = text = None
				if not line:
					break
			else:
				line = unicode(line.rstrip())
				if not trange and self.is_valid_timestamp_range(line):
					trange = self.get_timestamp_range(line)
				else:
					text = [] if text is None else text
					text.append(line)
		return result
