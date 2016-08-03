#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from nti.externalization.representation import WithRepr

from nti.schema.eqhash import EqHash

from nti.schema.fieldproperty import createDirectFieldProperties

from .interfaces import ITimeContentPointer
from .interfaces import ITimeRangeDescription
from .interfaces import ITranscriptContentPointer
from .interfaces import ITranscriptRangeDescription

from .contentrange import ContentPointer
from .contentrange import ContentRangeDescription

@interface.implementer(ITimeContentPointer)
@WithRepr
@EqHash("role", "seconds")
class TimeContentPointer(ContentPointer):
	__external_can_create__ = True
	mime_type = 'application/vnd.nextthought.contentrange.timecontentpointer'
	createDirectFieldProperties(ITimeContentPointer)

@interface.implementer(ITimeRangeDescription)
@WithRepr
@EqHash("seriesId", "start", "end")
class TimeRangeDescription(ContentRangeDescription):
	__external_can_create__ = True
	mime_type = 'application/vnd.nextthought.contentrange.timerangedescription'
	createDirectFieldProperties(ITimeRangeDescription)

@interface.implementer(ITranscriptContentPointer)
@WithRepr
@EqHash("pointer", "cueid")
class TranscriptContentPointer(TimeContentPointer):
	mime_type = 'application/vnd.nextthought.contentrange.transcriptcontentpointer'
	createDirectFieldProperties(ITranscriptContentPointer)

@interface.implementer(ITranscriptRangeDescription)
@WithRepr
@EqHash("start", "end")
class TranscriptRangeDescription(TimeRangeDescription):
	mime_type = 'application/vnd.nextthought.contentrange.transcriptrangedescription'
	createDirectFieldProperties(ITranscriptRangeDescription)
