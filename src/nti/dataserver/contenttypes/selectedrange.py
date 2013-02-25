#!/usr/bin/env python
"""
Definitions of selected range objects.
"""
from __future__ import print_function, unicode_literals

from zope import interface

from nti.utils.property import alias


from nti.dataserver import interfaces as nti_interfaces

from .base import UserContentRoot
from zope.schema.fieldproperty import FieldProperty

@interface.implementer(nti_interfaces.ISelectedRange)
class SelectedRange(UserContentRoot):
	"""
	Base implementation of selected ranges in the DOM. Intended to be used
	as a base class.
	"""

	# TODO: Use FieldProperties? Use SchemaConfiguredObject?
	selectedText = ''
	applicableRange = None

	# Tags. It may be better to use objects to represent
	# the tags and have a single list. The two-field approach
	# most directly matches what the externalization is.
	tags = FieldProperty(nti_interfaces.ISelectedRange['tags'])

	AutoTags = ()

	def __init__( self ):
		super(SelectedRange,self).__init__()



from .base import UserContentRootInternalObjectIO


class SelectedRangeInternalObjectIO(UserContentRootInternalObjectIO):
	"""
	Intended to be used as a base class.
	"""

	_excluded_in_ivars_ = { 'AutoTags' } | UserContentRootInternalObjectIO._excluded_in_ivars_
	_ext_primitive_out_ivars_ = {'selectedText'} |  UserContentRootInternalObjectIO._ext_primitive_out_ivars_


	def updateFromExternalObject( self, parsed, *args, **kwargs ):
		parsed.pop( 'AutoTags', None )

		super(SelectedRangeInternalObjectIO,self).updateFromExternalObject( parsed, *args, **kwargs )
