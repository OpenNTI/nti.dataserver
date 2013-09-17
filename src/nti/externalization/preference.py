#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Support for externalizing :mod:`zope.preference` objects.

These objects are used with schemas (defined by interfaces) that
define the possible preference values. The values are not directly
stored in the preference objects, but instead in annotations on the
owner of the preference; these are read and written as required. The
preference objects themselves implement
:class:`zope.preference.interfaces.IPreferenceGroup` as well as the
schema for the preference value.

.. note:: Because the preference schema is also implemented by the preference object,
  one should generally not also have externalizers registered
  for that interface. In other words, using exactly the same interface for
  a preference schema as is implemented by a model object is probably not a good
  idea.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope import component
from zope.preference.interfaces import IPreferenceGroup

from .interfaces import IInternalObjectIO
from .interfaces import StandardExternalFields
from .externalization import toExternalObject
from .datastructures import InterfaceObjectIO


@interface.implementer(IInternalObjectIO)
@component.adapter(IPreferenceGroup)
class PreferenceGroupObjectIO(InterfaceObjectIO):
	"""
	Externalizes preference groups using the existing interface schema.
	Our main job is to determine the correct schema to use and
	find the sub-groups.

	Class Names and MimeTypes
	=========================

	A second job is to determine the externally visible 'Class'
	and 'MimeType' values. We have no solid convention for deriving
	that from interface names, and in any case, in order to find
	the given incoming object from those values, we echo the (package-like)
	values of the preference group id (modified for convention).
	This overrides anything the specific subclass of PreferenceGroup
	or schema interface specified.

	"""

	# For the root object, the schema will be missing
	# and the id will be blank

	def __init__( self, context ):
		super(PreferenceGroupObjectIO,self).__init__( context,
													  iface_upper_bound=context.__schema__ or IPreferenceGroup )

	def toExternalObject(self, mergeFrom=None ):
		result = super(PreferenceGroupObjectIO,self).toExternalObject( mergeFrom=mergeFrom )
		context = self._ext_replacement()
		group_id = context.__id__ or 'Root'
		# Now fixup names
		# For class, '.' is often used as a delimiter in programming languages, and
		# we don't want to force everyone to mirror our hierarchy. So we use _.
		result[StandardExternalFields.CLASS] = 'Preference_' + group_id.replace( '.', '_' )

		# And similar for mimetype, except we already have
		# and use a dot convention
		result[StandardExternalFields.MIMETYPE] = 'application/vnd.nextthought.preference.' + group_id.lower()

		# Last but not least, add any registered sub-groups
		for local_name, group in context.items():
			assert local_name not in result, "Invalid group name, developer error"
			result[local_name] = toExternalObject( group )

		return result
