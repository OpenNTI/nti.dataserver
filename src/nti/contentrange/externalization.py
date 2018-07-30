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

from nti.externalization.datastructures import InterfaceObjectIO

from nti.externalization.interfaces import IInternalObjectIO

logger = __import__('logging').getLogger(__name__)


@component.adapter(IDomContentPointer)
class DomContentPointerExternal(InterfaceObjectIO):
    _ext_iface_upper_bound = IDomContentPointer
    __external_use_minimal_base__ = True


@component.adapter(ITextContext)
class TextContextExternal(InterfaceObjectIO):
    _ext_iface_upper_bound = ITextContext
    __external_use_minimal_base__ = True


@component.adapter(IContentRangeDescription)
class ContentRangeDescriptionExternal(InterfaceObjectIO):
    _ext_iface_upper_bound = IContentRangeDescription
    __external_use_minimal_base__ = True


@component.adapter(ITimeContentPointer)
class TimeContentPointerExternal(InterfaceObjectIO):
    _ext_iface_upper_bound = ITimeContentPointer
    __external_use_minimal_base__ = True


@component.adapter(ITimeRangeDescription)
class TimeRangeDescriptionExternal(InterfaceObjectIO):
    _ext_iface_upper_bound = ITimeRangeDescription
    __external_use_minimal_base__ = True


@component.adapter(ITranscriptContentPointer)
class TranscriptContentPointerExternal(InterfaceObjectIO):
    _ext_iface_upper_bound = ITranscriptContentPointer
    __external_use_minimal_base__ = True


@component.adapter(ITranscriptRangeDescription)
class TranscriptRangeDescriptionExternal(InterfaceObjectIO):
    _ext_iface_upper_bound = ITranscriptRangeDescription
    __external_use_minimal_base__ = True
