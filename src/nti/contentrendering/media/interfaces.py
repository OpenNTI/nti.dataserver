#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

from zope import schema
from zope import interface
from zope.interface.common.sequence import IMinimalSequence

from nti.utils import schema as nti_schema

class IMediaTranscriptEntry(interface.Interface):
	"""
	Marker interface for video transcript entry
	"""
	transcript = nti_schema.ValidText(title='Transcript text')
	end_timestamp = nti_schema.ValidTextLine(title='End time stamp')
	start_timestamp = nti_schema.ValidTextLine(title='Start time stamp')
	id = nti_schema.ValidTextLine(title='Transcript entry id', required=False)
	language = nti_schema.ValidTextLine(title='Transcript language', required=False,
										default='en')

class IAudioTranscriptEntry(IMediaTranscriptEntry):
	pass

class IVideoTranscriptEntry(IMediaTranscriptEntry):
	pass

class IMediaTranscript(IMinimalSequence):
	"""
	Marker interface for media transcript
	"""
	entries = nti_schema.ListOrTuple(schema.Object(IMediaTranscriptEntry, title='the entry'),
						  			 title='Ordered transcript entries')

class IAudioTranscript(IMediaTranscript):
	"""
	Marker interface for audio transcript
	"""
	entries = nti_schema.ListOrTuple(schema.Object(IAudioTranscriptEntry, title='the entry'),
						  			 title='Ordered transcript entries')

class IVideoTranscript(IMediaTranscript):
	"""
	Marker interface for video transcript
	"""
	entries = nti_schema.ListOrTuple(schema.Object(IVideoTranscriptEntry, title='the entry'),
						  			 title='Ordered transcript entries')


class IMediaTranscriptParser(interface.Interface):
	"""
	Marker interface for audio transcript parsers
	"""

	def parse(source):
		"""
		Parse the specified source
		
		:param source: Media transcript source
		:return a IMediaTranscript object
		"""

class IAudioTranscriptParser(IMediaTranscriptParser):
	"""
	Marker interface for audio transcript parsers
	"""

class IVideoTranscriptParser(IMediaTranscriptParser):
	"""
	Marker interface for video transcript parsers
	"""
