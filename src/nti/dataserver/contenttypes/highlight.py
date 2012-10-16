#!/usr/bin/env python
"""
Definitions of highlight objects.
"""
from __future__ import print_function, unicode_literals

from zope import interface
from zope.deprecation import deprecate


from nti.dataserver import interfaces as nti_interfaces

from .base import UserContentRoot
UserContentRoot = UserContentRoot # BWC top-level import
from .selectedrange import SelectedRange # BWC top-level import

class _HighlightBWC(object):
	"""
	Defines read-only properties that are included in a highlight
	to help backwards compatibility.
	"""

	top = left = startOffset = endOffset = property( deprecate( "Use the applicableRange" )( lambda self: 0 ) )

	highlightedText = startHighlightedFullText = startHighlightedText = endHighlightedText = endHighlightedFullText = property( deprecate( "Use the selectedText" )( lambda self: getattr( self, 'selectedText' ) ) )

	startXpath = startAnchor = endAnchor = endXpath = anchorPoint = anchorType = property( deprecate( "Use the applicableRange" )( lambda self: '' ) )


@interface.implementer(nti_interfaces.IHighlight)
class Highlight(SelectedRange, _HighlightBWC):
	"""
	Implementation of a highlight.
	"""
	_ext_primitive_out_ivars_ = SelectedRange._ext_primitive_out_ivars_.union( {'style'} )

	_schema_fields_to_validate_ = SelectedRange._schema_fields_to_validate_ + ('style',)
	_schema_to_validate_ = nti_interfaces.IHighlight


	style = nti_interfaces.IHighlight['style'].default

	def __init__( self ):
		super(Highlight,self).__init__()
		# To get in the dict for externalization
		self.style = self.style
