#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Containers specialized to work with intids.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)
from ZODB import loglevels

from zope import interface
from zope import component

import BTrees
from BTrees.Length import Length
import persistent

from zope.cachedescriptors.property import CachedProperty
from zope.cachedescriptors.property import Lazy

from zope.container.contained import Contained

from zope.location import interfaces as loc_interfaces
from zc import intid as zc_intid
from nti.utils import sets

from collections import Iterable, Container, Sized, Mapping
from UserDict import DictMixin

# Make pylint not complain about "badly implemented container", "Abstract class not referenced"
#pylint: disable=R0924,R0921

@interface.implementer(loc_interfaces.ILocation)
class _AbstractIntidResolvingFacade(object):
	"""
	Base class to support facades that resolve intids.
	"""

	__parent__ = None
	__name__ = None
	_intids = None

	def __init__( self, context, allow_missing=False, parent=None, name=None, intids=None ):
		"""
		:keyword bool allow_missing: If False (the default) then errors will be
			raised for objects that are in the set but cannot be found by id. If
			``True``, then they will be silently ignored.
		:keyword intids: If provided, this will be the intid utility we use. Otherwise, we
			will look one up at iteration time.
		"""
		self.context = context
		self._allow_missing = allow_missing
		if parent:
			self.__parent__ = parent
		if name:
			self.__name__ = name
		if intids is not None:
			self._intids = intids

	def __reduce__( self ):
		raise TypeError( "Transient object; should not be pickled" )


class IntidResolvingIterable(_AbstractIntidResolvingFacade, Iterable, Container, Sized):
	"""
	An iterable that wraps another iterable, resolving intids as it
	goes. Typically this will be a :mod:`BTrees` IISet of some family.
	"""

	def __iter__( self, allow_missing=None ):
		allow_missing = allow_missing or self._allow_missing
		intids = self._intids if self._intids is not None else component.getUtility( zc_intid.IIntIds )
		for iid in self.context:
			__traceback_info__ = iid, self.__parent__, self.__name__
			try:
				yield intids.getObject( iid )
			except TypeError:
				# Raised when we send a string or something, which means we do not actually
				# have an IISet. This is a sign of an object missed during migration
				if not allow_missing:
					raise
				logger.log( loglevels.TRACE, "Incorrect key '%s' in %r of %r", iid, self.__name__, self.__parent__ )
			except KeyError:
				if not allow_missing:
					raise
				logger.log( loglevels.TRACE, "Failed to resolve key '%s' in %r of %r", iid, self.__name__, self.__parent__ )

	def __len__( self ):
		return len(self.context)

	def __contains__( self, obj ):
		"""
		Is the given object in the container? This is implemented as a linear check.
		"""
		for other in self.__iter__( allow_missing=True ):
			if other == obj:
				return True

class IntidResolvingMappingFacade(_AbstractIntidResolvingFacade,DictMixin,Mapping):
	"""
	A read-only dict-like object wrapping another mapping (usually a :mod:`BTrees.family.OO.BTree`).
	The keys will typically be strings, and the values must be iterables of integers
	appropriate for use with the intid utility. (Usually they will be ``IISet`` objects.)
	"""

	def __wrap( self, key, val ):
		return IntidResolvingIterable( val, allow_missing=self._allow_missing, parent=self, name=key, intids=self._intids )

	def __getitem__( self, key ):
		return  self.__wrap( key, self.context[key] )

	def keys(self):
		return self.context.keys()

	def __contains__( self, key ):
		return key in self.context

	def __iter__( self ):
		return iter(self.context)

	def iteritems( self ):
		return ((k, self.__wrap( k, v )) for k, v in self.context.iteritems())

	def values(self):
		return (v for _, v in self.iteritems())

	def __len__(self):
		return len(self.context)

	def __repr__( self ):
		return '<%s %s/%s>' % (self.__class__.__name__, self.__parent__, self.__name__)

	def __setitem__( self, key, val ):
		raise TypeError('Immutable Object')

	def __delitem__( self, key ):
		raise TypeError('Immutable Object')

class _LengthIntidResolvingMappingFacade(IntidResolvingMappingFacade):

	def __init__( self, *args, **kwargs ):
		self._len = kwargs.pop( '_len' )
		super(_LengthIntidResolvingMappingFacade,self).__init__( *args, **kwargs )

	def __len__(self):
		return self._len()

_marker = object()

class IntidContainedStorage(persistent.Persistent, Contained, Iterable, Container, Sized):
	"""
	An object that implements something like the interface of
	:class:`nti.dataserver.datastructures.ContainedStorage`, but in a
	simpler form using only intids, and assuming that we never need to
	look objects up by container/localID pairs.

	.. note:: This class and API is provisional.

	"""

	family = BTrees.family64

	def __init__( self, family=None ):
		super(IntidContainedStorage,self).__init__()
		if family is not None:
			self.family = family
		else:
			intids = component.queryUtility( zc_intid.IIntIds )
			if intids is not None:
				self.family = intids.family

		# Map from string container ids to self.family.II.TreeSet
		# { 'containerId': II.TreeSet() }
		# The values in the TreeSet are the intids of the shared
		# objects. Remember that len() of them is not efficient.
		self._containers = self.family.OO.BTree()

	def __iter__( self ):
		return iter(self._containers)

	@Lazy
	def _IntidContainedStorage__len(self):
		l = Length()
		ol = len(self._containers)
		if ol > 0:
			l.change(ol)
		self._p_changed = True
		return l

	def __len__(self):
		return self.__len()

	@CachedProperty # TODO: Is this right? Are we sure that the volatile properties added will go away when ghosted?
	def containers(self):
		"""
		Returns an object that has a `values` method that iterates
		the list-like (immutable) containers.

		.. note:: It is not efficient to get the length of the list-like
			containers; it is however, efficient, to test their boolean
			status (empty or not) and to get the length of the overall returned
			object.
		"""
		return _LengthIntidResolvingMappingFacade( self._containers, allow_missing=True, parent=self, name='SharedContainedObjectStorage',
												   _len=self.__len)

	def _check_contained_object_for_storage( self, contained ):
		pass

	def _get_intid_for_object( self, contained, when_none=_marker ):
		if contained is None and when_none is not _marker:
			return when_none

		return self._get_intid_for_object_from_utility( contained )

	def _get_intid_for_object_from_utility(self, contained):
		return component.getUtility( zc_intid.IIntIds ).getId( contained )

	def addContainedObjectToContainer( self, contained, containerId='' ):
		"Defaults to the unnamed container"
		self._check_contained_object_for_storage( contained )

		container_set = self._containers.get( containerId )
		if container_set is None:
			_len = self.__len
			container_set = self.family.II.TreeSet()
			self._containers[containerId] = container_set
			_len.change(1)
		container_set.add( self._get_intid_for_object( contained ) )
		return contained

	def deleteContainedObjectIdFromContainer( self, intid, containerId ):
		container_set = self._containers.get( containerId )
		if container_set is not None:
			return sets.discard_p( container_set, intid )

	def deleteEqualContainedObjectFromContainer( self, contained, containerId='' ):
		"Defaults to the unnamed container"
		self._check_contained_object_for_storage( contained )
		if self.deleteContainedObjectIdFromContainer( self._get_intid_for_object( contained ), containerId ):
			return contained

	def addContainedObject( self, contained ):
		"Fetches the containerId from the object."
		return self.addContainedObjectToContainer( contained, contained.containerId )

	def deleteEqualContainedObject( self, contained, log_level=None ):
		"Fetches the containerId from the object."
		return self.deleteEqualContainedObjectFromContainer( contained, contained.containerId )

	def getContainer( self, containerId, defaultValue=None ):
		return self.containers.get( containerId, default=defaultValue )

	def popContainer( self, containerId, default=_marker ):
		try:
			_len = self.__len
			result = self._containers.pop( containerId )
			_len.change( -1 )
			return result
		except KeyError:
			if default is not _marker:
				return default
			raise

	def __repr__( self ):
		return '<%s at %s/%s>' % (self.__class__.__name__, self.__parent__, self.__name__ )

	## Some dict-like conveniences
	__getitem__ = getContainer
	get = getContainer
	pop = popContainer
	def __contains__(self, key):
		return key in self._containers
	def keys(self):
		return self._containers.keys()
	def values(self):
		return self.containers.values() # unwrapping
	def items(self):
		return self.containers.items() # unwrapping
