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
		if intids:
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
		intids = self._intids or component.getUtility( zc_intid.IIntIds )
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
		raise NotImplementedError()

	def __delitem__( self, key ):
		raise NotImplementedError()
