# -*- coding: utf-8 -*-
"""
video transcript parsers.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

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

	def fix_timestamp(self, ts):
		ts = ts.replace(',', '.')
		splits = ts.split(':')
		if splits and len(splits[0]) == 1:
			ts = '0' + ts
		return ts

	def is_valid_timestamp_range(self, s):
		result = self.trx_times_pattern.search(s)
		return result

	def get_timestamp_range(self, s):
		m = self.trx_times_pattern.search(s)
		if m is not None:
			g = m.groups()
			start_time = self.fix_timestamp(g[0])
			end_time = self.fix_timestamp(g[2])
			return (start_time, end_time)
		else:
			return None

	def _create_transcript_entry(self, text, trange, eid=None):
		transcript = '\n'.join(text)
		e = VideoTranscriptEntry(id=eid,
								 transcript=transcript,
								 start_timestamp=trange[0],
								 end_timestamp=trange[1])
		return e

@interface.implementer(media_interfaces.ISRTVideoTranscriptParser)
class _SRTVideoTranscriptParser(_YoutubeVideoTranscriptParser):

	def parse(self, source):
		if isinstance(source, six.string_types):
			source = StringIO(source)

		eid = trange = text = None
		result = VideoTranscript()
		for line in source:
			line = unicode(line.rstrip()) if line else u''
			if not line:
				if range and text:
					e = self._create_transcript_entry(text, trange, eid)
					result.entries.append(e)
				trange = text = None
			elif not trange and line.isdigit() :
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
		if isinstance(source, six.string_types):
			source = StringIO(source)

		trange = text = None
		result = VideoTranscript()
		for line in source:
			line = unicode(line.rstrip()) if line else u''
			if not line:
				if range and text:
					eid = unicode(len(result) + 1)
					e = self._create_transcript_entry(text, trange, eid)
					result.entries.append(e)
				trange = text = None
			elif self.is_valid_timestamp_range(line):
				trange = self.get_timestamp_range(line)
			else:
				text = [] if text is None else text
				text.append(line)
		return result
