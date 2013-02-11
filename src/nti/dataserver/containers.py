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
from random import randint

from zope import interface
from zope import component
from zope.location import interfaces as loc_interfaces
from zope.lifecycleevent.interfaces import IObjectModifiedEvent
from zope.container.interfaces import IContainerModifiedEvent
from zope.container.interfaces import IBTreeContainer
from zope.annotation import interfaces as annotation

from . import interfaces

from zope.container.btree import BTreeContainer
from zope.container.contained import uncontained
from zope.container.contained import NameChooser

from nti.zodb.minmax import NumericMaximum, ConstantZeroValue

_MAX_UNIQUEID_ATTEMPTS = 1000

class ExhaustedUniqueIdsError(Exception):
	pass

class _IdGenerationMixin(object):
	"""
	Mix this in to a BTreeContainer to provide id generation.
	"""

	#: The integer counter for generated ids.
	_v_nextid = 0

	def generateId(self, prefix='item', suffix='', rand_ceiling=999999999, _nextid=None):
		"""
		Returns an (string) ID not used yet by this folder. Use this method directly
		if you have no client-supplied name to use as a base. (If you have a meaningful
		or client-supplied name to use as a base, use an :class:`.INameChooser`.)

		The ID is unlikely to collide with other threads and clients.
		The IDs are sequential to optimize access to objects
		that are likely to have some relation (i.e., so objects created in the same
		transaction are stored in the same BTree bucket)
		"""
		# JAM: Based on code from Products.BTreeFolder2.BTreeFolder2
		tree = self._SampleContainer__data
		n = _nextid or self._v_nextid
		attempt = 0
		while True:
			if n % 4000 != 0 and n <= rand_ceiling: # TODO: 4000 is a magic number. The size of the bucket?
				the_id = '%s%d%s' % (prefix, n, suffix)
				if not tree.has_key(the_id):
					break
			n = randint(1, rand_ceiling)
			attempt = attempt + 1
			if attempt > _MAX_UNIQUEID_ATTEMPTS:
				# Prevent denial of service
				raise ExhaustedUniqueIdsError()
		self._v_nextid = n + 1
		return the_id

# Go ahead and mix this in to the base BTreeContainer
BTreeContainer.__bases__ = (_IdGenerationMixin,) + BTreeContainer.__bases__

# zope.container's NameChooser is registered on IWriteContainer, we override
@component.adapter(IBTreeContainer)
class IdGeneratorNameChooser(NameChooser):
	"""
	A name chooser that uses the built-in ID generator to create a name.
	It also uses dots instead of dashes, as the superclass does.
	"""

	def chooseName(self, name, obj):
		# Unfortunately, the superclass method is entirely
		# monolithic and we must replace it.

		container = self.context

		# convert to unicode and remove characters that checkName does not allow
		if not name:
			name = unicode( obj.__class__.__name__ ) # use __class__, not type(), to work with proxies
		name = unicode(name) # throw if conversion doesn't work
		name = name.strip() # no whitespace
		# remove bad characters
		name = name.replace('/', '.').lstrip('+@')

		# If it's clean, go with it
		if name not in container:
			self.checkName( name, obj )
			return name

		# otherwise, generate

		# If the name looks like a filename, as in BASE.EXT, then keep the ext part
		# after the random part
		dot = name.rfind('.')
		if dot >= 0:
			# if name is 'foo.jpg', suffix is '.jpg' and name is 'foo.'.
			# that way we separate the random part with a ., as in foo.1.jpg
			suffix = name[dot:]
			name = name[:dot + 1]
		else:
			name = name + '.'
			suffix = ''

		if suffix == '.':
			suffix = ''

		# If the suffix is already an int, increment that
		try:
			extid = int(suffix[1:])
			nextid = extid + 1
		except ValueError:
			nextid = None
		else:
			suffix = ''

		name = container.generateId( name, suffix, _nextid=nextid )
		# Make sure the name is valid.	We may have started with something bad.
		self.checkName(name, obj )
		return name


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
	Register this handler to update modification times when an object
	itself is modified.
	"""
	try:
		modified_object.updateLastMod()
	except AttributeError:
		# this is optional API
		pass

class EventlessLastModifiedBTreeContainer(LastModifiedBTreeContainer):
	"""
	A BTreeContainer that doesn't actually broadcast any events, because
	it doesn't actually take ownership of the objects. The objects must
	have their ``__name__`` and ``__parent__`` set by a real container.
	"""

	def __setitem__( self, key, value ):
		__traceback_info__ = key, value
		# Containers don't allow None; keys must be unicode
		if isinstance(key, str):
			try:
				key = unicode(key)
			except UnicodeError:
				raise TypeError( 'Key could not be converted to unicode' )
		elif not isinstance( key, unicode ):
			raise TypeError( "Key must be unicode" )
		if value is None:
			raise TypeError( 'Value must not be None' )

		# Super's _setitemf changes the length, so only do this if
		# it's not here already. To comply with the containers interface,
		# we cannot add duplicates
		old = self.get( key )
		if old is not None:
			if old is value:
				# no op
				return
			raise KeyError( key )
		self._setitemf( key, value )
		# TODO: Should I enforce anything with the __parent__ and __name__ of
		# the value? For example, parent is not None and __name__ == key?
		# We're probably more generally useful without those constraints,
		# but more specifically useful in certain scenarios with those constraints.

	def __delitem__( self, key ):
		# Just like the super implementation, but without
		# firing the 'uncontained' event
		l = self._BTreeContainer__len
		del self._SampleContainer__data[key]
		l.change(-1)


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
		if not isinstance( key, basestring ):
			raise TypeError( "Expected basestring instead of %s (%r)" % (type(key), key))
		self.key = unicode(key)
		self._lower_key = self.key.lower()

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

# As of BTrees 4.0.1, None is no longer allowed to be a key
# or even used in __contains__

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
		return key is not None and _tx_key_insen( key ) in self._SampleContainer__data

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
		if key is None: return default
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

from zope.site.interfaces import IFolder
from zope.site.site import SiteManagerContainer

@interface.implementer(IFolder)
class CaseInsensitiveLastModifiedBTreeFolder(CaseInsensitiveLastModifiedBTreeContainer, SiteManagerContainer):
	"""
	Scalable case-insensitive :class:`IFolder` implementation.
	"""
