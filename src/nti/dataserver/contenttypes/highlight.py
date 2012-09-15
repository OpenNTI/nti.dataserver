#!/usr/bin/env python
"""
Definitions of highlight objects.
"""
from __future__ import print_function, unicode_literals

from zope import interface
from zope.deprecation import deprecate


from nti.externalization.datastructures import ExternalizableInstanceDict
from nti.externalization import internalization

from nti.dataserver import interfaces as nti_interfaces

from .base import UserContentRoot

class _HighlightBWC(object):
	"""
	Defines read-only properties that are included in a highlight
	to help backwards compatibility.
	"""

	top = left = startOffset = endOffset = property( deprecate( "Use the applicableRange" )( lambda self: 0 ) )

	highlightedText = startHighlightedFullText = startHighlightedText = endHighlightedText = endHighlightedFullText = property( deprecate( "Use the selectedText" )( lambda self: getattr( self, 'selectedText' ) ) )

	startXpath = startAnchor = endAnchor = endXpath = anchorPoint = anchorType = property( deprecate( "Use the applicableRange" )( lambda self: '' ) )

@interface.implementer(nti_interfaces.IZContained, nti_interfaces.ISelectedRange)
class SelectedRange(UserContentRoot,ExternalizableInstanceDict):
	# See comments in UserContentRoot about being IZContained. We add it here to minimize the impact

	_excluded_in_ivars_ = { 'AutoTags' } | ExternalizableInstanceDict._excluded_in_ivars_
	_ext_primitive_out_ivars_ = ExternalizableInstanceDict._ext_primitive_out_ivars_.union( {'selectedText'} )

	selectedText = ''
	applicableRange = None
	tags = ()
	AutoTags = ()
	_update_accepts_type_attrs = True
	__parent__ = None

	def __init__( self ):
		super(SelectedRange,self).__init__()
		# To get in the dict for externalization
		self.selectedText = ''
		self.applicableRange = None

		# Tags. It may be better to use objects to represent
		# the tags and have a single list. The two-field approach
		# most directly matches what the externalization is.
		self.tags = ()
		self.AutoTags = ()

	__name__ = property(lambda self: getattr( self, 'id'), lambda self, name: setattr( self, 'id', name ))

	# While we are transitioning over from instance-dict-based serialization
	# to schema based serialization and validation, we handle update validation
	# ourself through these two class attributes. You may extend the list of fields
	# to validate in your subclass if you also set the schema to the schema that defines
	# those fields (and inherits from ISelectedRange).
	# This validation provides an opportunity for adaptation to come into play as well,
	# automatically taking care of things like sanitizing user input
	_schema_fields_to_validate_ = ('applicableRange', 'selectedText')
	_schema_to_validate_ = nti_interfaces.ISelectedRange

	def updateFromExternalObject( self, parsed, *args, **kwargs ):
		parsed.pop( 'AutoTags', None )
		super(SelectedRange,self).updateFromExternalObject( parsed, *args, **kwargs )
		__traceback_info__ = parsed
		for k in self._schema_fields_to_validate_:
			value = getattr( self, k )
			# pass the current value, and call the return value (if there's no exception)
			# in case adaptation took place
			internalization.validate_named_field_value( self, self._schema_to_validate_, k, value )()


		if 'tags' in parsed:
			# we lowercase and sanitize tags. Our sanitization here is really
			# cheap and discards html symbols
			temp_tags = { t.lower() for t in parsed['tags'] if '>' not in t and '<' not in t and '&' not in t }
			if not temp_tags:
				self.tags = ()
			else:
				# Preserve an existing mutable object if we have one
				if not self.tags:
					self.tags = []
				del self.tags[:]
				self.tags.extend( temp_tags )

@interface.implementer(nti_interfaces.IHighlight)
class Highlight(SelectedRange, _HighlightBWC):

	_ext_primitive_out_ivars_ = SelectedRange._ext_primitive_out_ivars_.union( {'style'} )

	style = 'plain'

	def __init__( self ):
		super(Highlight,self).__init__()
		# To get in the dict for externalization
		self.style = self.style

	def updateFromExternalObject( self, parsed, *args, **kwargs ):
		super(Highlight,self).updateFromExternalObject( parsed, *args, **kwargs )
		if 'style' in parsed:
			nti_interfaces.IHighlight['style'].validate( parsed['style'] )
