# -*- coding: utf-8 -*-
"""
Book indexing interfaces

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import schema
from zope import interface
from zope.interface.common.sequence import IMinimalSequence

from nti.utils import schema as nti_schema

class IVideoTranscriptEntry(interface.Interface):
	"""
	Marker interface for video transcript entry
	"""
	id = nti_schema.ValidTextLine(title='Transcript entry id', required=False)
	transcript = nti_schema.ValidText(title='Transcript text')
	start_timestamp = nti_schema.ValidTextLine(title='Start time stamp')
	end_timestamp = nti_schema.ValidTextLine(title='End time stamp')

class IVideoTranscript(IMinimalSequence):
	"""
	Marker interface for video transcript
	"""
	entries = schema.List(schema.Object(IVideoTranscriptEntry, title='the entry'), title='Order transcript entries')

class IVideoTranscriptParser(interface.Interface):
	"""
	Marker interface for video transcript parsers
	"""

	def parse(source):
		"""
		Parse the specified source
		
		:param source: Video transcript source
		:return a IVideoTranscript object
		"""

class ISRTVideoTranscriptParser(IVideoTranscriptParser):
	pass

class ISBVVideoTranscriptParser(IVideoTranscriptParser):
	pass
