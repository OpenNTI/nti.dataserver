#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Weak references to things with intids. These serve the same purpose as general
persistent weak references from :mod:`persistent.wref`, but are specific
to things with intids, and do not keep the object alive or accessible once
the object is removed from the intid catalog
(whereas weak refs do until such time as the database is GC'd).

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import warnings
import functools

from zope import component
from zope import interface

from zc.intid import IIntIds

from nti.wref.interfaces import ICachingWeakRef
from nti.wref.interfaces import IWeakRefToMissing

class _AbstractWeakRef(object):
	"""
	A weak reference to a content object (generally, anything
	with an intid). Call this object to return either the
	object, or if the object has gone away, ``None``.

	Subclasses need to support three properties: ``_entity_id``,
	``_entity_oid``, and ``_v_entity_cache``. The first is the intid.
	Because intids can be reused, we also include a backup, the
	object's OID (if it has one) in the second. This isn't foolproof,
	but should to pretty good. The third is used for caching.
	Subclasses will need to decide how to implement ``__getstate__``
	and ``__setstate__``. If subclasses need a __dict__, they will have
	to declare that in ``__slots__.``
	"""

	__slots__ = ()

	def __init__(self, content_object):
		self._entity_id = component.getUtility(IIntIds).getId(content_object)
		# _v_entity_cache is a volatile attribute. It's either None, meaning we have
		# no idea, the resolved object, or False
		self._v_entity_cache = content_object
		self._entity_oid = getattr(content_object, '_p_oid', None)

	def _cached(self, allow_cached):
		if allow_cached and self._v_entity_cache is not None:
			# Notice that we must explicitly check for _v_entity_cache being
			# not False, because we use False to represent a failed lookup. (But
			# we cannot use just a simple bool comparison because that fails for
			# something like an empty container)
			return self._v_entity_cache if self._v_entity_cache is not False else None

		try:
			result = component.getUtility(IIntIds).getObject(self._entity_id)
		except KeyError:
			result = None

		if self._entity_oid is not None:
			result_oid = getattr(result, '_p_oid', None)
			if result_oid is None or result_oid != self._entity_oid:
				result = None

		if allow_cached:  # only perturb the state if we are allowed to
			if result is not None:
				self._v_entity_cache = result
			else:
				self._v_entity_cache = False

		return result

	def __call__(self, allow_cached=True):
		return self._cached(allow_cached)

	def __eq__(self, other):
		if self is other: return True
		try:
			if self._entity_id == other._entity_id:
				return self._entity_oid == other._entity_oid or self._entity_oid is None
		except AttributeError:  # pragma: no cover
			return NotImplemented

	def __ne__(self, other):
		if self is other: return False
		eq = self.__eq__(other)
		if eq is NotImplemented:
			return eq
		return not eq

	def __hash__(self):
		return hash((self._entity_id, self._entity_oid))

	def __repr__(self):
		return "<%s.%s %s>" % (self.__class__.__module__,
							   self.__class__.__name__,
							   self._entity_id)

	def make_missing_ntiid(self):
		from nti.externalization.integer_strings import to_external_string

		from nti.ntiids.ntiids import TYPE_MISSING
		from nti.ntiids.ntiids import make_ntiid
		eid = self._entity_id
		# This intid is probably no longer used, but we have no guarantee
		# of that. We do some trivial manipulation on it to make it less
		# obvious what it is, and less likely to come into the system when
		# we don't want it to
		eid = to_external_string(eid)
		# base64 might be nice, but that doesn't play well with ntiids
		return make_ntiid(nttype=TYPE_MISSING, specific=eid)

@interface.implementer(IWeakRefToMissing, ICachingWeakRef)
class WeakRef(_AbstractWeakRef):
	"""
	A weak reference to a content object (generally, anything
	with an intid). Call this object to return either the
	object, or if the object has gone away, ``None``.

	Note that this is not a persistent object. It is not mutable (and
	it's also very tiny), and it has value semantics, so there's very
	little need to be persistent. This means it's suitable for use in
	OOSet objects and OOBTree objects as keys (if subclassed to provide
	total ordering!)
	"""

	__slots__ = ('_entity_id', '_entity_oid', '_v_entity_cache')

	def __getstate__(self):
		return self._entity_id, self._entity_oid

	def __setstate__(self, state):
		self._entity_id, self._entity_oid = state
		self._v_entity_cache = None

	# We are not orderable. Hopefully there is no data like this in the real
	# world, but we did have tests relying on it. Try to catch it here,
	# doing what python would have done itself.
	def __lt__(self, other):
		warnings.warn("Default WeakRef (to %s) is not totally orderable" % type(self()),
					  stacklevel=2)
		return id(self) < id(other)

	def __gt__(self, other):
		warnings.warn("Default WeakRef (to %s) is not totally orderable" % type(self()),
					  stacklevel=2)
		return id(self) > id(other)

@functools.total_ordering
class ArbitraryOrderableWeakRef(WeakRef):
	"""
	A subclass of :class:`WeakRef` that is orderable in a completely arbitrary
	way (based simply on intids).
	"""

	def __lt__(self, other):
		try:
			return (self._entity_id, self._entity_oid) < (other._entity_id, other._entity_oid)
		except AttributeError:
			return NotImplemented

	def __gt__(self, other):
		try:
			return (self._entity_id, self._entity_oid) > (other._entity_id, other._entity_oid)
		except AttributeError:
			return NotImplemented

class NoCachingArbitraryOrderableWeakRef(ArbitraryOrderableWeakRef):
	
		def __call__(self, allow_cached=False):
			return ArbitraryOrderableWeakRef.__call__(self, allow_cached=False)
