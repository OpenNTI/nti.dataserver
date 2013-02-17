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


@interface.implementer(nti_interfaces.IHighlight)
class Highlight(SelectedRange): #, _HighlightBWC):
	"""
	Implementation of a highlight.
	"""

	style = nti_interfaces.IHighlight['style'].default

	def __init__( self ):
		super(Highlight,self).__init__()
		# To get in the dict for externalization
		self.style = self.style

from .selectedrange import SelectedRangeInternalObjectIO

@component.adapter(nti_interfaces.IHighlight)
class HighlightInternalObjectIO(SelectedRangeInternalObjectIO):
	_ext_primitive_out_ivars_ = SelectedRangeInternalObjectIO._ext_primitive_out_ivars_.union( {'style'} )

	_schema_fields_to_validate_ = SelectedRangeInternalObjectIO._schema_fields_to_validate_ + ('style',)
	_schema_to_validate_ = nti_interfaces.IHighlight
