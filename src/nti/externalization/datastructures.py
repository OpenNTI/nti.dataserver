#!/usr/bin/env python
"""
Datastructures to help externalization.
$Revision$
"""
from __future__ import unicode_literals, print_function

import logging
logger = logging.getLogger( __name__ )

import ZODB

from zope import interface
from zope import component
from zope import schema
from zope.schema import interfaces as sch_interfaces
from zope.location import ILocation

from .interfaces import IExternalObject, IInternalObjectIO, ILocatedExternalMapping, ILocatedExternalSequence, StandardInternalFields, StandardExternalFields
from .externalization import to_standard_external_dictionary, toExternalObject

def _syntheticKeys( ):
	return ('OID', 'ID', 'Last Modified', 'Creator', 'ContainerId', 'Class')

def _isMagicKey( key ):
	""" For our mixin objects that have special keys, defines
	those keys that are special and not settable by the user. """
	return key in _syntheticKeys()

isSyntheticKey = _isMagicKey


class LocatedExternalDict(dict):
	"""
	A dictionary that implements ILocation. Returned
	by toExternalDictionary.
	"""
	interface.implements( ILocatedExternalMapping )
	__name__ = ''
	__parent__ = None
	__acl__ = ()

class LocatedExternalList(list):
	"""
	A list that implements ILocation. Returned
	by toExternalObject.
	"""
	interface.implements( ILocatedExternalSequence )
	__name__ = ''
	__parent__ = None
	__acl__ = ()

class ExternalizableDictionaryMixin(object):
	""" Implements a toExternalDictionary method as a base for subclasses. """

	def __init__(self, *args):
		super(ExternalizableDictionaryMixin,self).__init__(*args)

	def _ext_replacement( self ):
		return self

	def toExternalDictionary( self, mergeFrom=None):
		return to_standard_external_dictionary( self._ext_replacement(), mergeFrom=mergeFrom )

	def stripSyntheticKeysFromExternalDictionary( self, external ):
		""" Given a mutable dictionary, removes all the external keys
		that might have been added by toExternalDictionary and echoed back. """
		for k in _syntheticKeys():
			external.pop( k, None )
		return external

@interface.implementer(IInternalObjectIO)
class AbstractDynamicObjectIO(ExternalizableDictionaryMixin):
	"""
	Base class for objects that externalize based on dynamic information.

	Abstractions are in place to allow subclasses to map external and internal names
	independently (this type never uses getattr/setattr/hasattr, except for some
	standard fields).
	"""

	# TODO: there should be some better way to customize this if desired (an explicit list)
	# TODO: Play well with __slots__
	# TODO: This won't evolve well. Need something more sophisticated,
	# probably a meta class.

	# Avoid things super handles
	_excluded_out_ivars_ = {StandardInternalFields.ID, StandardExternalFields.ID, StandardInternalFields.CREATOR,
							StandardExternalFields.CREATOR, StandardInternalFields.CONTAINER_ID,
							'lastModified', StandardInternalFields.LAST_MODIFIEDU, StandardInternalFields.CREATED_TIME,
							'links'}
	_excluded_in_ivars_ = {StandardInternalFields.ID, StandardExternalFields.ID,
						   StandardExternalFields.OID,
						   StandardInternalFields.CREATOR,
						   StandardExternalFields.CREATOR,
						   'lastModified',
						   StandardInternalFields.LAST_MODIFIEDU,
						   StandardExternalFields.CLASS,
						   StandardInternalFields.CONTAINER_ID}
	_prefer_oid_ = False


	def _ext_all_possible_keys(self):
		raise NotImplementedError() # pragma: no cover

	def _ext_setattr( self, ext_self, k, value ):
		raise NotImplementedError() # pragma: no cover

	def _ext_getattr( self, ext_self, k ):
		"""
		Return the attributed of the `ext_self` object with the external name `k`.
		If the attribute does not exist, should raise.
		"""
		raise NotImplementedError() # pragma: no cover

	def _ext_keys(self):
		"""
		Return only the names of attributes that should be externalized.
		These values will be used as keys in the external dictionary.

		See :meth:_ext_all_possible_keys. This implementation then filters out
		*private* attributes (those beginning with an underscore),
		and those listed in `_excluded_in_ivars_.`
		"""
		#ext_self = self._ext_replacement()
		return 	[k for k in self._ext_all_possible_keys()
				 if (k not in self._excluded_out_ivars_  # specifically excluded
					 and not k.startswith( '_' ))]			# private
					 #and not callable(getattr(ext_self,k)))]	# avoid functions

	def toExternalDictionary( self, mergeFrom=None ):
		result = super(AbstractDynamicObjectIO,self).toExternalDictionary( mergeFrom=mergeFrom )
		ext_self = self._ext_replacement()
		for k in self._ext_keys():
			if k in result:
				# Standard key already added
				continue

			result[k] = toExternalObject( self._ext_getattr( ext_self, k ) )
			if ILocation.providedBy( result[k] ):
				result[k].__parent__ = ext_self

		if StandardExternalFields.ID in result and StandardExternalFields.OID in result \
			   and self._prefer_oid_ and result[StandardExternalFields.ID] != result[StandardExternalFields.OID]:
			result[StandardExternalFields.ID] = result[StandardExternalFields.OID]
		return result

	def toExternalObject( self, mergeFrom=None ):
		return self.toExternalDictionary(mergeFrom)

	def _ext_accept_update_key( self, k, ext_self, ext_keys ):
		"""
		Returns whether or not this key should be accepted for setting
		on the object, or silently ignored.
		:param ext_keys: As an optimization, the value of :meth:`_ext_all_possible_keys`
			is passed. Keys are only accepted if they are in this list.
		"""
		if k in self._excluded_in_ivars_:
			return False

		return k in ext_keys


	def updateFromExternalObject( self, parsed, *args, **kwargs ):
		ext_self = self._ext_replacement()
		ext_keys = self._ext_all_possible_keys()
		for k in parsed:
			if not self._ext_accept_update_key( k, ext_self, ext_keys ):
				continue

			self._ext_setattr( ext_self, k, parsed[k] )

		if StandardExternalFields.CONTAINER_ID in parsed and getattr( ext_self, StandardInternalFields.CONTAINER_ID, parsed ) is None:
			setattr( ext_self, StandardInternalFields.CONTAINER_ID, parsed[StandardExternalFields.CONTAINER_ID] )
		if StandardExternalFields.CREATOR in parsed and getattr( ext_self, StandardExternalFields.CREATOR, parsed ) is None:
			setattr( ext_self, StandardExternalFields.CREATOR, parsed[StandardExternalFields.CREATOR] )


@interface.implementer(IInternalObjectIO)
class ExternalizableInstanceDict(AbstractDynamicObjectIO):
	"""
	Externalizes to a dictionary containing the members of __dict__ that do not start with an underscore.

	Meant to be used as a super class; also can be used as an external object superclass.
	"""

	# TODO: there should be some better way to customize this if desired (an explicit list)
	# TODO: Play well with __slots__? ZODB supports slots, but doesn't recommend them
	# TODO: This won't evolve well. Need something more sophisticated,
	# probably a meta class.

	_update_accepts_type_attrs = False

	def _ext_all_possible_keys(self):
		return self._ext_replacement().__dict__.keys()

	def _ext_setattr( self, ext_self, k, value ):
		setattr( ext_self, k, value )

	def _ext_getattr( self, ext_self, k ):
		return getattr( ext_self, k )

	def _ext_accept_update_key( self, k, ext_self, ext_keys ):
		return super(ExternalizableInstanceDict,self)._ext_accept_update_key( k, ext_self, ext_keys ) \
		  or (self._update_accepts_type_attrs and hasattr( ext_self, k ))

	def __repr__( self ):
		try:
			return "%s().__dict__.update( %s )" % (self.__class__.__name__, self.toExternalDictionary() )
		except ZODB.POSException.ConnectionStateError:
			return '%s(Ghost)' % self.__class__.__name__
		except (ValueError,LookupError) as e: # Things like invalid NTIID, missing registrations
			return '%s(%s)' % (self.__class__.__name__, e)

@interface.implementer(IInternalObjectIO)
class InterfaceObjectIO(AbstractDynamicObjectIO):
	"""
	Externalizes to a dictionary based on getting the attributes of an
	object defined by an interface.

	Meant to be used as an adapter, so accepts the object to externalize in the constructor,
	as well as the interface to use to guide the process. The object is externalized
	using the most-derived version of the interface given to the constructor that it
	implements.

	(TODO: In the future extend this to multiple, non-overlapping interfaces, and better
	interface detection (see :class:`ModuleScopedInterfaceObjectIO` for a limited version of this.)
	"""

	def __init__( self, ext_self, iface_upper_bound=None ):
		super(InterfaceObjectIO, self).__init__( )
		self._ext_self = ext_self
		# TODO: Should we cache the schema we use for a particular type?
		self._iface = self._ext_find_schema( ext_self, iface_upper_bound )

	def _ext_find_schema( self, ext_self, iface_upper_bound ):
		_iface = iface_upper_bound
		# Search for the most derived version of the interface
		# this object implements and use that.
		for iface in interface.providedBy( ext_self ):
			if iface.isOrExtends( _iface ):
				_iface = iface
		return _iface

	def _ext_schemas_to_consider( self, ext_self ):
		return interface.providedBy( ext_self )

	def _ext_replacement( self ):
		return self._ext_self

	def _ext_all_possible_keys(self):
		return list(self._iface)

	def _ext_getattr( self, ext_self, k ):
		# TODO: Should this be directed through IField.get?
		return getattr( ext_self, k )

	def _ext_setattr( self, ext_self, k, value ):
		field = self._iface[k]
		if sch_interfaces.IField.providedBy( field ):
			# A schema field means we have info to validate it.
			# Do so.
			field = field.bind( ext_self )
			field.validate( value )
			field.set( ext_self, value )
		else:
			setattr( ext_self, k, value )


	def updateFromExternalObject( self, parsed, *args, **kwargs ):
		super(InterfaceObjectIO,self).updateFromExternalObject( parsed, *args, **kwargs )
		# If we make it this far, then validate the object.
		# TODO: Should probably just make sure that there are no /new/ validation errors added
		errors = schema.getValidationErrors( self._iface, self._ext_self )
		if errors:
			raise errors[0][1]


class ModuleScopedInterfaceObjectIO(InterfaceObjectIO):
	"""
	Only considers the interfaces provided within a given module (usually declared
	as a class attribute) when searching for the schema to use to externalize an object;
	the most derived version of interfaces within that module will be used.

	Suitable for use when all the externalizable fields of interest are declared by an
	interface within a module, and an object does not implement two unrelated interfaces
	from the same module.
	"""

	_ext_search_module = None

	def _ext_find_schema( self, ext_self, iface_upper_bound ):
		# If the upper bound is given, then let the super class handle it all.
		# Presumably the user has given the correct branch to search.
		if iface_upper_bound is not None:
			return super(ModuleScopedInterfaceObjectIO,self)._ext_find_schema( ext_self, iface_upper_bound )

		most_derived = super(ModuleScopedInterfaceObjectIO,self)._ext_find_schema( ext_self, interface.Interface )
		# In theory, this is now the most derived interface.
		# If we have a tree that is non-linear, though, it may not be.
		# In that case, we are not suitable for use with this object
		for iface in self._ext_schemas_to_consider( ext_self ):
			if not most_derived.isOrExtends( iface ):
				raise TypeError( "Non-linear interface tree implemented by %s in %s: %s is not %s" % (type(ext_self),self._ext_search_module, most_derived, iface))
		return most_derived

	def _ext_schemas_to_consider( self, ext_self ):
		return (x for x in interface.providedBy( ext_self ) if x.__module__ == self._ext_search_module.__name__)
