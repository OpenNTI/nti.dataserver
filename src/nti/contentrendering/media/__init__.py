# -*- coding: utf-8 -*-
"""
video transcript parsers.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from nti.utils.schema import SchemaConfigured
from nti.utils.schema import createDirectFieldProperties

from . import interfaces as media_interfaces

@interface.implementer(media_interfaces.IVideoTranscriptEntry)
class VideoTranscriptEntry(SchemaConfigured):
	createDirectFieldProperties(media_interfaces.IVideoTranscriptEntry)

	def __str__(self):
		return "%s,%s,%s" % (self.id, self.start_timestamp, self.end_timestamp)

	def __repr__(self):
		return "%s(%s,%s,%s\n%s)" % (self.__class__.__name__,
									 self.id,
									 self.start_timestamp,
									 self.end_timestamp,
									 self.transcript)

@interface.implementer(media_interfaces.IVideoTranscript)
class VideoTranscript(object):

	def __init__(self):
		self.entries = []

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
