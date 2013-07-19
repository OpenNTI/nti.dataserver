#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Externalization support for the content range objects.

Note that these are very frequently written, so we take some shortcuts
and only write the minimal base and avoid interface-based decoration.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"


from zope import interface
from zope import component

from nti.externalization.interfaces import IInternalObjectIO
from nti.externalization.datastructures import InterfaceObjectIO

from . import interfaces

from nti.externalization.internalization import register_legacy_search_module
register_legacy_search_module('nti.contentrange.contentrange')

@interface.implementer(IInternalObjectIO)
@component.adapter(interfaces.IDomContentPointer)
class DomContentPointerExternal(InterfaceObjectIO):
	_ext_iface_upper_bound = interfaces.IDomContentPointer
	__external_use_minimal_base__ = True

@interface.implementer(IInternalObjectIO)
@component.adapter(interfaces.ITextContext)
class TextContextExternal(InterfaceObjectIO):
	_ext_iface_upper_bound = interfaces.ITextContext
	__external_use_minimal_base__ = True

@interface.implementer(IInternalObjectIO)
@component.adapter(interfaces.IContentRangeDescription)
class ContentRangeDescriptionExternal(InterfaceObjectIO):
	_ext_iface_upper_bound = interfaces.IContentRangeDescription
	__external_use_minimal_base__ = True


@interface.implementer(IInternalObjectIO)
@component.adapter(interfaces.ITimeContentPointer)
class TimeContentPointerExternal(InterfaceObjectIO):
	_ext_iface_upper_bound = interfaces.ITimeContentPointer
	__external_use_minimal_base__ = True

@interface.implementer(IInternalObjectIO)
@component.adapter(interfaces.ITimeRangeDescription)
class TimeRangeDescriptionExternal(InterfaceObjectIO):
	_ext_iface_upper_bound = interfaces.ITimeRangeDescription
	__external_use_minimal_base__ = True

@interface.implementer(IInternalObjectIO)
@component.adapter(interfaces.ITranscriptContentPointer)
class TranscriptContentPointerExternal(InterfaceObjectIO):
	_ext_iface_upper_bound = interfaces.ITranscriptContentPointer
	__external_use_minimal_base__ = True

@interface.implementer(IInternalObjectIO)
@component.adapter(interfaces.ITranscriptRangeDescription)
class TranscriptRangeDescriptionExternal(InterfaceObjectIO):
	_ext_iface_upper_bound = interfaces.ITranscriptRangeDescription
	__external_use_minimal_base__ = True
