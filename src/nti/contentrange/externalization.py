#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Externalization support for the content range objects.

$Id$
"""
from __future__ import print_function, unicode_literals


from zope import interface
from zope import component

#from nti.externalization.datastructures import LocatedExternalDict
#from nti.externalization.externalization import toExternalObject
from nti.externalization.datastructures import InterfaceObjectIO
from nti.externalization.interfaces import IInternalObjectIO #, StandardExternalFields
from nti.contentrange import interfaces


from nti.externalization.internalization import register_legacy_search_module
register_legacy_search_module('nti.contentrange.contentrange')


@interface.implementer(IInternalObjectIO)
@component.adapter(interfaces.IDomContentPointer)
class DomContentPointerExternal(InterfaceObjectIO):
	"""
	"""
	_ext_iface_upper_bound = interfaces.IDomContentPointer

@interface.implementer(IInternalObjectIO)
@component.adapter(interfaces.ITextContext)
class TextContextExternal(InterfaceObjectIO):
	"""
	"""
	_ext_iface_upper_bound = interfaces.ITextContext

@interface.implementer(IInternalObjectIO)
@component.adapter(interfaces.IContentRangeDescription)
class ContentRangeDescriptionExternal(InterfaceObjectIO):
	"""
	"""
	_ext_iface_upper_bound = interfaces.IContentRangeDescription
