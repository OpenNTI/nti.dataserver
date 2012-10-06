#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Weak references to entities. These serve the same purpose as general
persistent weak references from :mod:`persistent.wref`, but are specific
to entity objects, and do not keep the entity alive or accessible once
the entity is deleted (whereas weak refs do until such time as the database is
GC'd).

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import functools

from zope import component
from zope import interface
from zc import intid as zc_intid

from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.users import missing_user

@functools.total_ordering
@interface.implementer(nti_interfaces.IWeakRef)
@component.adapter(nti_interfaces.IEntity)
class WeakRef(object):
	"""
	A weak reference to an entity object (generally, anything
	with a username). Call this object to return either the
	entity object, or if the entity has gone away, None.

	Note that this is not a persistent object. It is not mutable (and it's also
	very tiny), and it has value semantics, so there's very little need to be persistent.
	This means it's suitable for use in OOSet objects and OOBTree objects as keys.

	Instances define the following attributes:

	.. py:attribute:: username

		The username being referenced.

	.. todo:: This is very similar to :class:`nti.dataserver.intid_wref.WeakRef`.

	"""

	# Because entity names may be reused, we keep both the intid of the object
	# as well as the username and only return the entity if both of those things match.

	__slots__ = ('username', '_entity_id', '_v_entity_cache')

	def __init__( self, entity ):
		self.username = entity.username.lower()
		self._entity_id = component.getUtility( zc_intid.IIntIds ).getId( entity )
		# _v_entity_cache is a volatile attribute. It's either None, meaning we have
		# no idea, the resolved Entity object, or False
		self._v_entity_cache = entity

	def __getstate__( self ):
		return self.username, self._entity_id

	def __setstate__( self, state ):
		self.username, self._entity_id = state
		self._v_entity_cache = None

	def _cached(self):
		if self._v_entity_cache is not None:
			return self._v_entity_cache if self._v_entity_cache else None

		try:
			result = component.getUtility( zc_intid.IIntIds ).getObject( self._entity_id )
		except KeyError:
			result = None

		result_username = getattr( result, 'username', None )
		if result_username is None or result_username.lower() != self.username:
			result = None

		if result is not None:
			self._v_entity_cache = result
		else:
			self._v_entity_cache = False

		return result

	def __call__(self, return_missing_proxy=False ):
		"""
		Return the entity object, or None if it no longer exists.

		:param bool return_missing_proxy: If set to ``True``, then this will
			return a :mod:`nti.dataserver.users.missing_user` proxy instead of
			None. You can also set this to a callable object to return
			a different type of object.
		"""
		result = self._cached()

		if result is None and return_missing_proxy:
			factory = return_missing_proxy if callable(return_missing_proxy) else missing_user.MissingEntity
			result = factory( self.username )

		return result

	def __eq__( self, other ):
		try:
			return self is other or (self.username == other.username and self._entity_id == other._entity_id)
		except AttributeError: #pragma: no cover
			return NotImplemented

	def __lt__( self, other ):
		try:
			return self.username < other.username and self._entity_id < other._entity_id
		except AttributeError: # pragma: no cover
			return NotImplemented

	def __gt__( self, other ):
		try:
			return self.username > other.username and self._entity_id > other._entity_id
		except AttributeError: # pragma: no cover
			return NotImplemented

	def __hash__(self):
		return hash(self.username) + self._entity_id

	def __repr__(self):
		return "<%s.%s %s/%s>" % (self.__class__.__module__, self.__class__.__name__, self.username, self._entity_id)

	# TODO: Consider making this object act like a proxy for the entity if its found.
