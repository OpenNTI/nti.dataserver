#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
media transcript parsers.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from nti.utils.schema import SchemaConfigured
from nti.schema.fieldproperty import createDirectFieldProperties

from . import interfaces as media_interfaces

@interface.implementer(media_interfaces.IMediaTranscriptEntry)
class MediaTranscriptEntry(SchemaConfigured):
	createDirectFieldProperties(media_interfaces.IMediaTranscriptEntry)

	def __str__(self):
		return "%s,%s,%s" % (self.id, self.start_timestamp, self.end_timestamp)

	def __repr__(self):
		return "%s(%s,%s,%s\n%s)" % (self.__class__.__name__,
									 self.id,
									 self.start_timestamp,
									 self.end_timestamp,
									 self.transcript)

@interface.implementer(media_interfaces.IAudioTranscriptEntry)
class AudioTranscriptEntry(MediaTranscriptEntry):
	createDirectFieldProperties(media_interfaces.IAudioTranscriptEntry)

@interface.implementer(media_interfaces.IVideoTranscriptEntry)
class VideoTranscriptEntry(MediaTranscriptEntry):
	createDirectFieldProperties(media_interfaces.IVideoTranscriptEntry)

@interface.implementer(media_interfaces.IMediaTranscript)
class MediaTranscript(SchemaConfigured):
	createDirectFieldProperties(media_interfaces.IMediaTranscript)

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

@interface.implementer(media_interfaces.IAudioTranscript)
class AudioTranscript(MediaTranscript):
	createDirectFieldProperties(media_interfaces.IAudioTranscript)

@interface.implementer(media_interfaces.IVideoTranscript)
class VideoTranscript(MediaTranscript):
	createDirectFieldProperties(media_interfaces.IVideoTranscript)
