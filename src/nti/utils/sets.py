#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Utilities for working with sets.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

def discard( the_set, the_value ):
	"""
	A version of :meth:`set.discard` that works not just on :class:`set` objects,
	but also on :class:`BTrees.OOBTree.OOTreeSet` (and the smaller :class:`BTrees.OOBTree.OOSet`,
	plus the sets in other families). (It incidentally works on lists, though not efficiently.)

	:param set the_set: The :class:`set` or set-like thing.
	:param the_value: The object to remove from `the_set`. If the object isn't
		present in the set, no exception will be raised.
	:return: Undefined.
	"""
	try:
		the_set.discard( the_value ) # python sets
	except AttributeError:
		try:
			the_set.remove( the_value ) # BTrees..[Tree]Set. Also, python list
		except (KeyError,ValueError): pass

def discard_p( the_set, the_value ):
	"""
	A version of :meth:`set.discard` that functions as a predicate by returning
	whether or not the object was removed from the set. In addition to working on :class:`set` objects,
	it also works on :class:`BTrees.OOBTree.OOTreeSet` (and the smaller :class:`BTrees.OOBTree.OOSet`,
	plus the sets in other families). (It incidentally works on lists, though not efficiently.)

	:param set the_set: The :class:`set` or set-like thing.
	:param the_value: The object to remove from `the_set`. If the object isn't
		present in the set, no exception will be raised.
	:return: A true value if `the_value` was present in the set and has now
		been removed; a false value if `the_value` was not present in the set.
	"""
	try:
		# Both set and OOSet support remove with the same semantics
		the_set.remove( the_value )
		return True # TODO: Is there a more useful value to return? If so document it
	except KeyError:
		return False

import collections

SLICE_ALL = slice(None)

def is_iterable(obj):
	"""
	Are we being asked to look up a list of things, instead of a single thing?
	We check for the `__iter__` attribute so that this can cover types that
	don't have to be known by this module, such as NumPy arrays.

	Strings, however, should be considered as atomic values to look up, not
	iterables.

	We don't need to check for the Python 2 `unicode` type, because it doesn't
	have an `__iter__` attribute anyway.
	"""
	return hasattr(obj, '__iter__') and not isinstance(obj, str)

class OrderedSet(collections.MutableSet):
	"""
	An OrderedSet is a custom MutableSet that remembers its order, so that
	every entry has an index that can be looked up.
	
	based on 
		https://pypi.python.org/pypi/ordered-set/1.3 
		http://code.activestate.com/recipes/576694-orderedset/
	"""
	def __init__(self, iterable=None):
		self.items = []
		self.map = {}
		if iterable is not None:
			self |= iterable

	def __len__(self):
		return len(self.items)

	def __getitem__(self, index):
		"""
		Get the item at a given index.

		If `index` is a slice, you will get back that slice of items. If it's
		the slice [:], exactly the same object is returned. (If you want an
		independent copy of an OrderedSet, use `OrderedSet.copy()`.)

		If `index` is an iterable, you'll get the OrderedSet of items
		corresponding to those indices. This is similar to NumPy's
		"fancy indexing".
		"""
		if index == SLICE_ALL:
			return self
		elif hasattr(index, '__index__') or isinstance(index, slice):
			result = self.items[index]
			if isinstance(result, list):
				return OrderedSet(result)
			else:
				return result
		elif is_iterable(index):
			return OrderedSet([self.items[i] for i in index])
		else:
			raise TypeError("Don't know how to index an OrderedSet by %r" %
					index)

	def copy(self):
		return OrderedSet(self)

	def __getstate__(self):
		if len(self) == 0:
			return (None,)
		else:
			return list(self)
	
	def __setstate__(self, state):
		if state == (None,):
			self.__init__([])
		else:
			self.__init__(state)

	def __contains__(self, key):
		return key in self.map

	def add(self, key):
		"""
		Add `key` as an item to this OrderedSet, then return its index.

		If `key` is already in the OrderedSet, return the index it already
		had.
		"""
		if key not in self.map:
			self.map[key] = len(self.items)
			self.items.append(key)
		return self.map[key]
	append = add
	
	def index(self, key):
		"""
		Get the index of a given entry, raising an IndexError if it's not
		present.

		`key` can be an iterable of entries that is not a string, in which case
		this returns a list of indices.
		"""
		if is_iterable(key):
			return [self.index(subkey) for subkey in key]
		return self.map[key]

	def discard(self, key):
		raise NotImplementedError(
			"Cannot remove items from an existing OrderedSet"
		)

	def __iter__(self):
		return iter(self.items)

	def __reversed__(self):
		return reversed(self.items)

	def __repr__(self):
		if not self:
			return '%s()' % (self.__class__.__name__,)
		return '%s(%r)' % (self.__class__.__name__, list(self))

	def __eq__(self, other):
		if isinstance(other, OrderedSet):
			return len(self) == len(other) and self.items == other.items
		return set(self) == set(other)
