#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from nti.schema.schema import SchemaConfigured
from nti.schema.fieldproperty import createDirectFieldProperties

from .interfaces import IAudioTranscript
from .interfaces import IMediaTranscript
from .interfaces import IVideoTranscript
from .interfaces import IAudioTranscriptEntry
from .interfaces import IMediaTranscriptEntry
from .interfaces import IVideoTranscriptEntry

@interface.implementer(IMediaTranscriptEntry)
class MediaTranscriptEntry(SchemaConfigured):
	createDirectFieldProperties(IMediaTranscriptEntry)

	def __str__(self):
		return "%s,%s,%s" % (self.id, self.start_timestamp, self.end_timestamp)

	def __repr__(self):
		return "%s(%s,%s,%s\n%s)" % (self.__class__.__name__,
									 self.id,
									 self.start_timestamp,
									 self.end_timestamp,
									 self.transcript)

@interface.implementer(IAudioTranscriptEntry)
class AudioTranscriptEntry(MediaTranscriptEntry):
	createDirectFieldProperties(IAudioTranscriptEntry)

@interface.implementer(IVideoTranscriptEntry)
class VideoTranscriptEntry(MediaTranscriptEntry):
	createDirectFieldProperties(IVideoTranscriptEntry)

@interface.implementer(IMediaTranscript)
class MediaTranscript(SchemaConfigured):
	createDirectFieldProperties(IMediaTranscript)

	def __getitem__(self, index):
		return self.entries[index]

	def __len__(self):
		return len(self.entries)

	def __str__(self):
		return "%s" % len(self)

	def __repr__(self):
		return "%s(%s)" % (self.__class__.__name__, self.entries)

	def __iter__(self):
		return iter(self.entries)

@interface.implementer(IAudioTranscript)
class AudioTranscript(MediaTranscript):
	createDirectFieldProperties(IAudioTranscript)

@interface.implementer(IVideoTranscript)
class VideoTranscript(MediaTranscript):
	createDirectFieldProperties(IVideoTranscript)
