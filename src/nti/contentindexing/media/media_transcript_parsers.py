#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
media transcript parsers.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import re
import six
from cStringIO import StringIO

from .web_vtt_parser import WebVTTParser

from . import MediaTranscript
from . import MediaTranscriptEntry

class _BaseTranscriptParser(object):

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
	def fix_source(cls, source):
		if isinstance(source, six.string_types):
			source = StringIO(source)
		return source

class _YoutubeTranscriptParser(_BaseTranscriptParser):

	entry_cls = MediaTranscriptEntry

	@classmethod
	def get_timestamp_range(cls, s):
		m = cls.trx_times_pattern.search(s)
		if m is not None:
			g = m.groups()
			start_time = cls.fix_timestamp(g[0])
			end_time = cls.fix_timestamp(g[2])
			return (start_time, end_time)
		return None

	@classmethod
	def create_transcript_entry(cls, text, trange, eid=None):
		transcript = '\n'.join(text)
		e = cls.entry_cls(id=eid,
						  transcript=transcript,
						  start_timestamp=trange[0],
						  end_timestamp=trange[1])
		return e

class _SRTTranscriptParser(_YoutubeTranscriptParser):

	transcript_cls = MediaTranscript

	@classmethod
	def parse(cls, source):
		entries = []
		eid = trange = text = None
		source = cls.fix_source(source)
		while True:
			line = source.readline()
			if not line or not line.strip():
				if range and text:
					e = cls.create_transcript_entry(text, trange, eid)
					entries.append(e)
				eid = trange = text = None
				if not line:
					break
			else:
				line = unicode(line.rstrip())
				if not trange and line.isdigit() :
					eid = line
				elif not trange and cls.is_valid_timestamp_range(line):
					trange = cls.get_timestamp_range(line)
				else:
					text = [] if text is None else text
					text.append(line)
		result = cls.transcript_cls(entries=entries)
		return result

class _SBVTranscriptParser(_YoutubeTranscriptParser):

	transcript_cls = MediaTranscript

	@classmethod
	def parse(cls, source):
		entries = []
		trange = text = None
		source = cls.fix_source(source)
		while True:
			line = source.readline()
			if not line or not line.strip():
				if range and text:
					eid = unicode(len(entries) + 1)
					e = cls.create_transcript_entry(text, trange, eid)
					entries.append(e)
				trange = text = None
				if not line:
					break
			else:
				line = unicode(line.rstrip())
				if not trange and cls.is_valid_timestamp_range(line):
					trange = cls.get_timestamp_range(line)
				else:
					text = [] if text is None else text
					text.append(line)
		result = cls.transcript_cls(entries=entries)
		return result

class _WebVttTranscriptParser(_BaseTranscriptParser):

	entry_cls = MediaTranscriptEntry
	transcript_cls = MediaTranscript

	@classmethod
	def parse(cls, source):
		entries = []
		source = cls.fix_source(source)
		parser = WebVTTParser()
		parsed = parser.parse(source)
		cues = parsed.get('cues', [])
		for eid, cue in enumerate(cues):
			if cue.has_errors or not cue.end_timestamp or not cue.start_timestamp:
				continue
			e = cls.entry_cls(id=unicode(eid + 1),
							  transcript=unicode(cue.text),
							  start_timestamp=cue.start_timestamp,
							  end_timestamp=cue.end_timestamp)
			entries.append(e)
		result = cls.transcript_cls(entries=entries)
		return result
