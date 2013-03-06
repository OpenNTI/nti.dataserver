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

from zope.location import interfaces as loc_interfaces
from zc import intid as zc_intid

# Make pylint not complain about "badly implemented container"
#pylint: disable=R0924

@interface.implementer(loc_interfaces.ILocation)
class IntidResolvingIterable(object):
	"""
	An iterable that wraps another iterable, resolving intids as it goes.
	"""

	__parent__ = None
	__name__ = None
	_intids = None

	def __init__( self, iiset, allow_missing=False, parent=None, name=None, intids=None ):
		"""
		:param iiset: An iterable of intids. Typically this will be a
			:mod:`BTrees` IISet of some family.

		:keyword bool allow_missing: If False (the default) then errors will be
			raised for objects that are in the set but cannot be found by id. If
			``True``, then they will be silently ignored.
		:keyword intids: If provided, this will be the intid utility we use. Otherwise, we
			will look one up at iteration time.
		"""
		self._container_set = iiset
		self._allow_missing = allow_missing
		if parent:
			self.__parent__ = parent
		if name:
			self.__name__ = name
		if intids:
			self._intids = intids

	def __iter__( self ):
		intids = self._intids or component.getUtility( zc_intid.IIntIds )
		for iid in self._container_set:
			__traceback_info__ = iid, self.__parent__, self.__name__
			try:
				yield intids.getObject( iid )
			except TypeError:
				# Raised when we send a string or something, which means we do not actually
				# have an IISet. This is a sign of an object missed during migration
				if not self._allow_missing:
					raise
				logger.log( loglevels.TRACE, "Incorrect key '%s' in %r of %r", iid, self.__name__, self.__parent__ )
			except KeyError:
				if not self._allow_missing:
					raise
				logger.log( loglevels.TRACE, "Failed to resolve key '%s' in %r of %r", iid, self.__name__, self.__parent__ )

	def __len__( self ):
		return len(self._container_set)

	def __reduce__( self ):
		raise TypeError( "Transient object; should not be pickled" )
