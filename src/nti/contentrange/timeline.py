#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import interface

from . import interfaces

from nti.externalization.externalization import make_repr

from . import contentrange

from nti.utils.schema import createDirectFieldProperties

@interface.implementer(interfaces.ITimeContentPointer)
class TimeContentPointer(contentrange.ContentPointer):
	__external_can_create__ = True
	mime_type = 'application/vnd.nextthought.contentrange.timecontentpointer'
	createDirectFieldProperties(interfaces.ITimeContentPointer)

	__repr__ = make_repr()

	def __eq__(self, other):
		try:
			return self is other or (self.role == other.role
									 and self.seconds == other.seconds)
		except AttributeError:
			return NotImplemented

	def __hash__(self):
		return hash((self.role, self.seconds))


@interface.implementer(interfaces.ITimeRangeDescription)
class TimeRangeDescription(contentrange.ContentRangeDescription):
	__external_can_create__ = True
	mime_type = 'application/vnd.nextthought.contentrange.timerangedescription'
	createDirectFieldProperties(interfaces.ITimeRangeDescription)

	__repr__ = make_repr()

	def __eq__(self, other):
		try:
			return self is other or (self.seriesId == other.seriesId
									 and self.start == other.start
									 and self.end == other.end)
		except AttributeError:
			return NotImplemented

	def __hash__(self):
		return hash((self.seriesId, self.start, self.end))

@interface.implementer(interfaces.ITranscriptContentPointer)
class TranscriptContentPointer(TimeContentPointer):
	mime_type = 'application/vnd.nextthought.contentrange.transcriptcontentpointer'
	createDirectFieldProperties(interfaces.ITranscriptContentPointer)

	__repr__ = make_repr()

	def __eq__(self, other):
		try:
			return super(TranscriptContentPointer, self).__eq__(other) and (self.pointer == other.pointer
									 									and self.cueid == other.cueid)
		except AttributeError:
			return NotImplemented

	def __hash__(self):
		return hash((self.pointer, self.cueid))

@interface.implementer(interfaces.ITranscriptRangeDescription)
class TranscriptRangeDescription(TimeRangeDescription):
	mime_type = 'application/vnd.nextthought.contentrange.transcriptrangedescription'
	createDirectFieldProperties(interfaces.ITranscriptRangeDescription)

	def __eq__(self, other):
		try:
			return super(TranscriptRangeDescription, self).__eq__(other) and (self.start == other.start
									 										  and self.end == other.end)
		except AttributeError:
			return NotImplemented

	def __hash__(self):
		return hash((self.start, self.end))

	__repr__ = make_repr()
