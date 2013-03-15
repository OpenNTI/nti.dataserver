#!/usr/bin/env python
"""
Definitions of highlight objects.
"""
from __future__ import print_function, unicode_literals

from zope import interface
from zope import component

from nti.dataserver import interfaces as nti_interfaces

from .base import UserContentRoot
UserContentRoot = UserContentRoot # BWC top-level import
from .selectedrange import SelectedRange # BWC top-level import
from nti.utils.schema import createDirectFieldProperties

@interface.implementer(nti_interfaces.IHighlight)
class Highlight(SelectedRange): #, _HighlightBWC):
	"""
	Implementation of a highlight.
	"""

	createDirectFieldProperties(nti_interfaces.IHighlight) # style


	def __init__( self ):
		super(Highlight,self).__init__()

from .selectedrange import SelectedRangeInternalObjectIO

@component.adapter(nti_interfaces.IHighlight)
class HighlightInternalObjectIO(SelectedRangeInternalObjectIO):
	_ext_primitive_out_ivars_ = { 'style' } | SelectedRangeInternalObjectIO._ext_primitive_out_ivars_
