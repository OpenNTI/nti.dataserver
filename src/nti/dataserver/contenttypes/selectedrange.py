#!/usr/bin/env python
"""
Definitions of selected range objects.
"""
from __future__ import print_function, unicode_literals

from zope import interface

from nti.utils.property import alias


from nti.dataserver import interfaces as nti_interfaces

from .base import UserContentRoot

# See comments in UserContentRoot about being IZContained. We add it here to minimize the impact
@interface.implementer(nti_interfaces.IZContained, nti_interfaces.ISelectedRange)
class SelectedRange(UserContentRoot):
	"""
	Base implementation of selected ranges in the DOM. Intended to be used
	as a base class.
	"""

	selectedText = ''
	applicableRange = None
	tags = ()
	AutoTags = ()


	__parent__ = None
	__name__ = alias('id')


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



from .base import UserContentRootInternalObjectIO
from nti.externalization import internalization

class SelectedRangeInternalObjectIO(UserContentRootInternalObjectIO):
	"""
	Intended to be used as a base class.

	While we are transitioning over from instance-dict-based serialization
	to schema based serialization and validation, we handle update validation
	ourself through the class attributes :attr:`_schema_to_validate_` and
	:attr:`_schema_fields_to_validate_`. The former defines the schema to check against,
	and the latter is a tuple of fields to validate, defined by that schema.
	"""

	#: This class attribute works with :attr:`_schema_fields_to_validate_` to determine
	#: the schema object to use to validate fields. It should name a schema
	#: class that inherits from :class:`~nti.dataserver.interfaces.ISelectedRange` and defines any additional fields
	#: that are named in :attr:`_schema_fields_to_validate_`
	_schema_to_validate_ = nti_interfaces.ISelectedRange

	#: Tuple of field names defined by :attr:`_schema_to_validate_` that will be
	#: validated from external data.
	#: This validation provides an opportunity for adaptation to come into play as well,
	#: automatically taking care of things like sanitizing user input
	_schema_fields_to_validate_ = ('applicableRange', 'selectedText')


	_excluded_in_ivars_ = { 'AutoTags' } | UserContentRootInternalObjectIO._excluded_in_ivars_
	_ext_primitive_out_ivars_ = UserContentRootInternalObjectIO._ext_primitive_out_ivars_.union( {'selectedText'} )
	_update_accepts_type_attrs = True



	def updateFromExternalObject( self, parsed, *args, **kwargs ):
		parsed.pop( 'AutoTags', None )
		super(SelectedRangeInternalObjectIO,self).updateFromExternalObject( parsed, *args, **kwargs )
		__traceback_info__ = parsed


		for k in self._schema_fields_to_validate_:
			value = getattr( self.context, k )
			# pass the current value, and call the return value (if there's no exception)
			# in case adaptation took place
			internalization.validate_named_field_value( self.context, self._schema_to_validate_, k, value )()


		if 'tags' in parsed:
			# we lowercase and sanitize tags. Our sanitization here is really
			# cheap and discards html symbols
			temp_tags = { t.lower() for t in parsed['tags'] if '>' not in t and '<' not in t and '&' not in t }
			if not temp_tags:
				self.context.tags = ()
			else:
				# Preserve an existing mutable object if we have one
				if not self.context.tags:
					self.context.tags = []
				del self.context.tags[:]
				self.context.tags.extend( temp_tags )
