#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Externalization support for the content range objects.

Note that these are very frequently written, so we take some shortcuts
and only write the minimal base and avoid interface-based decoration.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import interface
from zope import component

from nti.contentrange.interfaces import ITextContext
from nti.contentrange.interfaces import IDomContentPointer
from nti.contentrange.interfaces import ITimeContentPointer
from nti.contentrange.interfaces import ITimeRangeDescription
from nti.contentrange.interfaces import IContentRangeDescription
from nti.contentrange.interfaces import ITranscriptContentPointer
from nti.contentrange.interfaces import ITranscriptRangeDescription

from nti.contentrange.contentrange import TextContext
from nti.contentrange.contentrange import DomContentPointer
from nti.contentrange.contentrange import ContentRangeDescription

from nti.contentrange.timeline import TimeContentPointer
from nti.contentrange.timeline import TimeRangeDescription
from nti.contentrange.timeline import TranscriptContentPointer
from nti.contentrange.timeline import TranscriptRangeDescription

from nti.externalization.datastructures import InterfaceObjectIO

from nti.externalization.interfaces import IInternalObjectIO
from nti.externalization.interfaces import IClassObjectFactory

logger = __import__('logging').getLogger(__name__)


@component.adapter(IDomContentPointer)
@interface.implementer(IInternalObjectIO)
class DomContentPointerExternal(InterfaceObjectIO):
    _ext_iface_upper_bound = IDomContentPointer
    __external_use_minimal_base__ = True


@component.adapter(ITextContext)
@interface.implementer(IInternalObjectIO)
class TextContextExternal(InterfaceObjectIO):
    _ext_iface_upper_bound = ITextContext
    __external_use_minimal_base__ = True


@interface.implementer(IInternalObjectIO)
@component.adapter(IContentRangeDescription)
class ContentRangeDescriptionExternal(InterfaceObjectIO):
    _ext_iface_upper_bound = IContentRangeDescription
    __external_use_minimal_base__ = True


@component.adapter(ITimeContentPointer)
@interface.implementer(IInternalObjectIO)
class TimeContentPointerExternal(InterfaceObjectIO):
    _ext_iface_upper_bound = ITimeContentPointer
    __external_use_minimal_base__ = True


@interface.implementer(IInternalObjectIO)
@component.adapter(ITimeRangeDescription)
class TimeRangeDescriptionExternal(InterfaceObjectIO):
    _ext_iface_upper_bound = ITimeRangeDescription
    __external_use_minimal_base__ = True


@interface.implementer(IInternalObjectIO)
@component.adapter(ITranscriptContentPointer)
class TranscriptContentPointerExternal(InterfaceObjectIO):
    _ext_iface_upper_bound = ITranscriptContentPointer
    __external_use_minimal_base__ = True


@interface.implementer(IInternalObjectIO)
@component.adapter(ITranscriptRangeDescription)
class TranscriptRangeDescriptionExternal(InterfaceObjectIO):
    _ext_iface_upper_bound = ITranscriptRangeDescription
    __external_use_minimal_base__ = True


@interface.implementer(IClassObjectFactory)
class ContentRangeFactoryMixin(object):
    factory = None
    provided = None
    description = title = "Content range object factory"

    def __init__(self, *args):
        pass

    def __call__(self, *unused_args, **unused_kw):
        return self.factory()

    def getInterfaces(self):
        return (self.provided,)


class DomContentPointerFactory(ContentRangeFactoryMixin):
    factory = DomContentPointer
    provided = IDomContentPointer


class TextContextFactory(ContentRangeFactoryMixin):
    factory = TextContext
    provided = ITextContext


class ContentRangeDescriptionFactory(ContentRangeFactoryMixin):
    factory = ContentRangeDescription
    provided = IContentRangeDescription


class TimeContentPointerFactory(ContentRangeFactoryMixin):
    factory = TimeContentPointer
    provided = ITimeContentPointer


class TimeRangeDescriptionFactory(ContentRangeFactoryMixin):
    factory = TimeRangeDescription
    provided = ITimeRangeDescription


class TranscriptContentPointerFactory(ContentRangeFactoryMixin):
    factory = TranscriptContentPointer
    provided = ITranscriptContentPointer
   

class TranscriptRangeDescriptionFactory(ContentRangeFactoryMixin):
    factory = TranscriptRangeDescription
    provided = ITranscriptRangeDescription
