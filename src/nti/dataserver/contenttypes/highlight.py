#!/usr/bin/env python
"""
Definitions of highlight objects.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope import component

from nti.dataserver import interfaces as nti_interfaces

from .base import UserContentRoot
UserContentRoot = UserContentRoot # BWC top-level import

from .selectedrange import SelectedRange # BWC top-level import
from nti.schema.fieldproperty import createDirectFieldProperties

from .color import createColorProperty
from .color import updateColorFromExternalValue

@interface.implementer(nti_interfaces.IHighlight)
class Highlight(SelectedRange): #, _HighlightBWC):
	"""
	Implementation of a highlight.
	"""

	createDirectFieldProperties(nti_interfaces.IHighlight,
								omit=('fillColor', 'fillOpacity', 'fillRGBAOpacity')) # style
	createColorProperty('fill', r=0.882, g=0.956, b=0.996)

	def __init__( self ):
		super(Highlight,self).__init__()

from .selectedrange import SelectedRangeInternalObjectIO

@component.adapter(nti_interfaces.IHighlight)
class HighlightInternalObjectIO(SelectedRangeInternalObjectIO):
	_ext_primitive_out_ivars_ = { 'style' } | SelectedRangeInternalObjectIO._ext_primitive_out_ivars_


	def updateFromExternalObject( self, ext_parsed, *args, **kwargs ):
		updateColorFromExternalValue(self.context, 'fill', ext_parsed)
		SelectedRangeInternalObjectIO.updateFromExternalObject(self, ext_parsed, *args, **kwargs)
