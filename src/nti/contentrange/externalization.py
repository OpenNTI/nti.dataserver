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
class _DomContentPointerExternal(InterfaceObjectIO):

	# The known subclasses use ivars that match
	_update_accepts_type_attrs = True
	def __init__( self, pointer ):
		super(_DomContentPointerExternal,self).__init__( pointer, interfaces.IDomContentPointer )


@interface.implementer(IInternalObjectIO)
@component.adapter(interfaces.ITextContext)
class _TextContextExternal(InterfaceObjectIO):
	_update_accepts_type_attrs = True
	def __init__( self, context ):
		super(_TextContextExternal,self).__init__( context, interfaces.ITextContext )


@interface.implementer(IInternalObjectIO)
@component.adapter(interfaces.IContentRangeDescription)
class _ContentRangeDescriptionExternal(InterfaceObjectIO):

	# It so happens that ContentRange and DomContentRange
	# have ivars that match what we need
	_update_accepts_type_attrs = True
	def __init__( self, the_range ):
		super(_ContentRangeDescriptionExternal,self).__init__( the_range, interfaces.IContentRangeDescription )
