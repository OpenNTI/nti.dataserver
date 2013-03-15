#!/usr/bin/env python
"""
Definitions of selected range objects.
"""
from __future__ import print_function, unicode_literals

from zope import interface


from nti.dataserver import interfaces as nti_interfaces

from .base import UserContentRoot
from nti.utils.schema import createDirectFieldProperties

@interface.implementer(nti_interfaces.ISelectedRange)
class SelectedRange(UserContentRoot):
	"""
	Base implementation of selected ranges in the DOM. Intended to be used
	as a base class.
	"""

	createDirectFieldProperties(nti_interfaces.IAnchoredRepresentation) # applicableRange
	createDirectFieldProperties(nti_interfaces.ISelectedRange) # selectedText
	# Tags. It may be better to use objects to represent
	# the tags and have a single list. The two-field approach
	# most directly matches what the externalization is.
	createDirectFieldProperties(nti_interfaces.IUserTaggedContent) # tags
	AutoTags = () # not currently in any interface

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
