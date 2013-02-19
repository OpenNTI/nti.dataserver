#!/usr/bin/env python
"""
Definitions of selected range objects.
"""
from __future__ import print_function, unicode_literals

from zope import interface

from nti.utils.property import alias


from nti.dataserver import interfaces as nti_interfaces

from .base import UserContentRoot

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
	tags = ()
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
		__traceback_info__ = parsed

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
