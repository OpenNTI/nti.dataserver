#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Implementations of :mod:`zope.container` containers.

Subclassing a BTree is not recommended (and leads to conflicts), so this takes alternate approachs
to tracking modification date information and implementing case
insensitivity.

$Id$
"""

from __future__ import print_function, unicode_literals

import time
import collections
import numbers

from zope import interface
from zope import component
from zope.location import interfaces as loc_interfaces
from zope.lifecycleevent.interfaces import IObjectModifiedEvent
from zope.container.interfaces import IContainerModifiedEvent
from zope.container.btree import BTreeContainer
from zope.container.contained import uncontained
from zope.annotation import interfaces as annotation


from . import interfaces

from nti.zodb.minmax import NumericMaximum, ConstantZeroValue


@interface.implementer(interfaces.ILastModified,annotation.IAttributeAnnotatable)
class LastModifiedBTreeContainer(BTreeContainer):
	"""
	A BTreeContainer that provides storage for lastModified and created
	attributes (implements the :class:`interfaces.ILastModified` interface).

	Note that directly changing keys within this container does not actually
	change those dates; instead, we rely on event listeners to
	notice ObjectEvents and adjust the times appropriately.

	These objects are allowed to be annotated (see :mod:`zope.annotation`).
	"""

	createdTime = 0
	_lastModified = ConstantZeroValue()

	def __init__( self ):
		self.createdTime = time.time()
		self._lastModified = NumericMaximum(value=0)
		super(LastModifiedBTreeContainer,self).__init__()

	def _get_lastModified(self):
		return self._lastModified.value
	def _set_lastModified(self, lm):
		# NOTE: Changing this value through the property
		# will result in false conflicts. Call the setter instead.
		self._lastModified.value = lm
	lastModified = property( _get_lastModified, _set_lastModified )

	def updateLastMod(self, t=None ):
		self._set_lastModified( t if t is not None and t > self.lastModified else time.time() )
		return self.lastModified

	def updateLastModIfGreater( self, t ):
		"Only if the given time is (not None and) greater than this object's is this object's time changed."
		if t is not None and t > self.lastModified:
			self._set_lastModified( t )
		return self.lastModified


	# We know that these methods are implemented as iterators

	def itervalues(self):
		return self.values()

	def iterkeys(self):
		return self.keys()

	def iteritems(self):
		return self.items()

collections.Mapping.register( LastModifiedBTreeContainer )

@component.adapter( interfaces.ILastModified, IContainerModifiedEvent )
def update_container_modified_time( container, event ):
	"""
	Register this handler to update modification times when a container is
	modified through addition or removal of children.
	"""
	container.updateLastMod()

@component.adapter( interfaces.ILastModified, IObjectModifiedEvent )
def update_parent_modified_time( modified_object, event ):
	"""
	If an object is modified and it is contained inside a container
	that wants to track modifications, we want to update its parent too.
	"""

	if interfaces.IZContained.providedBy( modified_object ) and interfaces.ILastModified.providedBy( modified_object.__parent__ ):
		modified_object.__parent__.updateLastMod()

@component.adapter( interfaces.ILastModified, IObjectModifiedEvent )
def update_object_modified_time( modified_object, event ):
	"""
	Register this handler to update modification times when a container is
	modified through addition or removal of children.
	"""
	try:
		modified_object.updateLastMod()
	except AttributeError:
		# this is optional API
		pass


import functools
@functools.total_ordering
class _CaseInsensitiveKey(object):
	"""
	This class implements a dictionary key that preserves case, but
	compares case-insensitively. It works with unicode keys only (BTrees do not
	work if 8-bit and unicode are mixed) by converting all keys to unicode.

	This is a bit of a heavyweight solution. It is nonetheless optimized for comparisons
	only with other objects of its same type. It must not be subclassed.
	"""

	def __init__( self, key ):
		self.key = unicode(key)
		self._lower_key = key.lower()

	def __str__( self ): # pragma: no cover
		return self.key

	def __repr__( self ): # pragma: no cover
		return "%s('%s')" % (self.__class__, self.key)

	# These should only ever be compared to themselves

	def __eq__(self, other):
		try:
			return other is self or other._lower_key == self._lower_key
		except AttributeError: # pragma: no cover
			return NotImplemented

	def __lt__(self, other):
		try:
			return self._lower_key < other._lower_key
		except AttributeError: # pragma: no cover
			return NotImplemented

	def __gt__(self, other):
		try:
			return self._lower_key > other._lower_key
		except AttributeError: # pragma: no cover
			return NotImplemented

from repoze.lru import lru_cache

# These work best as plain functions so that the 'self'
# argument is not captured. The self argument is persistent
# and so that messes with caches

@lru_cache(10000)
def _tx_key_insen(key):
	return _CaseInsensitiveKey( key ) if key is not None else None

@interface.implementer(loc_interfaces.ISublocations)
class CaseInsensitiveLastModifiedBTreeContainer(LastModifiedBTreeContainer):
	"""
	A BTreeContainer that only works with string (unicode) keys, and treats them in a case-insensitive
	fashion. The original case of the key entered is preserved.
	"""

	# For speed, we generally implement all these functions directly in terms of the
	# underlying data; we know that's what the superclass does.

	# Note that the IContainer contract specifies keys that are strings. None is not allowed.

	def __contains__( self, key ):
		return _tx_key_insen( key ) in self._SampleContainer__data

	def __iter__( self ):
		# For purposes of evolving, when our parent container
		# class has changed from one that used to manually wrap keys to
		# one that depends on us, we trap attribute errors. This should only
		# happen during the initial migration.
		for k in self._SampleContainer__data:
			__traceback_info__ = self, k
			try:
				yield k.key
			except AttributeError: # pragma: no cover
				if k == 'Last Modified': continue
				yield k


	def __getitem__( self, key ):
		return self._SampleContainer__data[_tx_key_insen(key)]

	def get( self, key, default=None ):
		return self._SampleContainer__data.get( _tx_key_insen( key ), default )

	def _setitemf( self, key, value ):
		LastModifiedBTreeContainer._setitemf( self, _tx_key_insen( key ), value )

	def __delitem__(self, key):
		# deleting is somewhat complicated by the need to broadcast
		# events with the original case
		l = self._BTreeContainer__len
		item = self[key]
		uncontained(item, self, item.__name__)
		del self._SampleContainer__data[_tx_key_insen(key)]
		l.change(-1)

	def items( self, key=None ):
		if key is not None:
			key = _tx_key_insen( key )

		for k, v in self._SampleContainer__data.items(key):
			try:
				yield k.key, v
			except AttributeError: # pragma: no cover
				if k == 'Last Modified': continue
				yield k, v

	def keys(self, key=None ):
		if key is not None:
			key = _tx_key_insen( key )
		return (k.key for k in self._SampleContainer__data.keys(key))

	def values( self, key=None ):
		if key is not None:
			key = _tx_key_insen( key )
		return (v for v in self._SampleContainer__data.values(key))

	def sublocations(self):
		# We directly implement ISublocations instead of using the adapter for two reasons.
		# First, it's much more efficient as it saves the unwrapping
		# of all the keys only to rewrap them back up to access the data.
		# Second, during evolving, as with __iter__, we may be in an inconsistent state
		# that has keys of different types
		for v in self._SampleContainer__data.values():
			# For evolving, reject numbers (Last Modified key)
			if isinstance( v, numbers.Number ): # pragma: no cover
				continue
			yield v
