#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Weak references to things with intids. These serve the same purpose as general
persistent weak references from :mod:`persistent.wref`, but are specific
to things with intids, and do not keep the object alive or accessible once
the object is removed from the intid catalog
(whereas weak refs do until such time as the database is GC'd).

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


from zope import component
from zope import interface
from zc import intid as zc_intid

from nti.dataserver import interfaces as nti_interfaces

@interface.implementer(nti_interfaces.IWeakRef)
class WeakRef(object):
	"""
	A weak reference to a content object (generally, anything
	with an intid). Call this object to return either the
	object, or if the object has gone away, None.

	Note that this is not a persistent object. It is not mutable (and it's also
	very tiny), and it has value semantics, so there's very little need to be persistent.
	This means it's suitable for use in OOSet objects and OOBTree objects as keys.

	"""

	# Because intids can be reused, we also include a backup,
	# the object's OID (if it has one). This isn't foolproof, but should to
	# pretty good
	__slots__ = ('_entity_id', '_entity_oid', '_v_entity_cache')

	def __init__( self, content_object ):
		self._entity_id = component.getUtility( zc_intid.IIntIds ).getId( content_object )
		# _v_entity_cache is a volatile attribute. It's either None, meaning we have
		# no idea, the resolved object, or False
		self._v_entity_cache = content_object
		self._entity_oid = getattr( content_object, '_p_oid', None )

	def __getstate__( self ):
		return self._entity_id, self._entity_oid

	def __setstate__( self, state ):
		self._entity_id, self._entity_oid = state
		self._v_entity_cache = None

	def _cached(self):
		if self._v_entity_cache is not None:
			return self._v_entity_cache if self._v_entity_cache else None

		try:
			result = component.getUtility( zc_intid.IIntIds ).getObject( self._entity_id )
		except KeyError:
			result = None

		if self._entity_oid is not None:
			result_oid = getattr( result, '_p_oid', None )
			if result_oid is None or result_oid != self._entity_oid:
				result = None

		if result is not None:
			self._v_entity_cache = result
		else:
			self._v_entity_cache = False

		return result

	def __call__(self):
		"""
		Return the content object, or None if it no longer exists.
		"""
		result = self._cached()

		return result

	def __eq__( self, other ):
		if self is other: return True
		try:
			if self._entity_id == other._entity_id:
				return self._entity_oid == other._entity_oid or self._entity_oid is None
		except AttributeError: #pragma: no cover
			return NotImplemented


	def __hash__(self):
		return hash((self._entity_id,self._entity_oid))

	def __repr__(self):
		return "<%s.%s %s>" % (self.__class__.__module__, self.__class__.__name__, self._entity_id)
