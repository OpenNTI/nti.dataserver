#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Classes and functions for dealing with persistence in an external context.

$Id$
"""
from __future__ import print_function, unicode_literals

import logging
logger = logging.getLogger( __name__ )


import collections

import persistent
import persistent.mapping
import persistent.wref
import persistent.list
from persistent.wref import WeakRef as PWeakRef


from zope import interface

from zope.container._zope_container_contained import isProxy as _isContainedProxy
from zope.container._zope_container_contained import getProxiedObject as _getContainedProxiedObject


from zope.security.management import system_user


from . import datastructures
from .externalization import toExternalObject
from .interfaces import IExternalObject
from .oids import toExternalOID


def getPersistentState( obj ):
	"""
	For a :class:`persistent.Persistent` object, returns one of the
	constants from the persistent module for its state:
	:const:`persistent.CHANGED` and :const:`persistent.UPTODATE` being the most useful.

	If the object is not Persistent and doesn't implement a ``getPersistentState`` method,
	this method will be pessimistic and assume the object has
	been :const:`persistent.CHANGED`.
	"""
	if hasattr( obj, '_p_changed' ):
		if getattr(obj, '_p_changed', False ):
			# Trust the changed value ahead of the state value,
			# because it is settable from python but the state
			# is more implicit.
			return persistent.CHANGED
		if getattr( obj, '_p_state', -1 ) == persistent.UPTODATE and getattr( obj, '_p_jar', -1 ) is None:
			# In keeping with the pessimistic theme, if it claims to be uptodate, but has never
			# been saved, we consider that the same as changed
			return persistent.CHANGED
		# We supply container classes that wrap objects (that are not IContained/ILocation)
		# in ContainerProxy classes. The proxy doesn't proxy _p_changed, which
		# leads to weird behaviour for things that want to notice changes (users.User.endUpdates)
		# so we need to reflect those changes to the actual object ourself
		# TODO: Such places should be using events
		if _isContainedProxy(obj):
			return getPersistentState( _getContainedProxiedObject( obj ) )
		return persistent.UPTODATE
	if hasattr(obj, '_p_state'):
		return getattr(obj, '_p_state' )
	return obj.getPersistentState() if hasattr( obj, 'getPersistentState' ) else persistent.CHANGED


def setPersistentStateChanged( obj ):
	""" Explicitly marks a persistent object as changed. """
	if hasattr(obj, '_p_changed' ):
		setattr(obj, '_p_changed', True )


def _weakRef_toExternalObject(self):
	val = self()
	if val is None:
		return None
	return toExternalObject( val )

persistent.wref.WeakRef.toExternalObject = _weakRef_toExternalObject
interface.classImplements( persistent.wref.WeakRef, IExternalObject )


def _weakRef_toExternalOID(self):
	val = self()
	if val is None:
		return None
	return toExternalOID( val )

persistent.wref.WeakRef.toExternalOID = _weakRef_toExternalOID


class PersistentExternalizableDictionary(persistent.mapping.PersistentMapping,datastructures.ExternalizableDictionaryMixin):
	"""
	Dictionary mixin that provides :meth:`toExternalDictionary` to return a new dictionary
	with each value in the dict having been externalized with
	:func:`toExternalObject`.
	"""
	def __init__(self, dict=None, **kwargs ):
		super(PersistentExternalizableDictionary, self).__init__( dict, **kwargs )

	def toExternalDictionary( self, mergeFrom=None):
		result = super(PersistentExternalizableDictionary,self).toExternalDictionary( self )
		for key, value in self.iteritems():
			result[key] = toExternalObject( value )
		return result

class PersistentExternalizableList(persistent.list.PersistentList):
	"""
	List mixin that provides :meth:`toExternalList` to return a new list
	with each element in the sequence having been externalized with
	:func:`toExternalObject`.
	"""

	def __init__(self, initlist=None):
		# Must use new-style super call to get right behaviour
		super(PersistentExternalizableList,self).__init__(initlist)

	def toExternalList( self ):
		result = [toExternalObject(x) for x in self if x is not None]
		return result

	def values(self):
		"""
		For compatibility with :mod:`zope.generations.utility`, this object
		defines a `values` method which does nothing but return itself. That
		makes these objects transparent and suitable for migrations.
		"""
		return self


class PersistentExternalizableWeakList(PersistentExternalizableList):
	"""
	Stores :class:`persistent.Persistent` objects as weak references, invisibly to the user.
	Any weak references added to the list will be treated the same.

	Weak references are resolved on access; if the referrant has been deleted, then that
	access will return ``None``.
	"""

	def __init__(self, initlist=None):
		if initlist is not None:
			initlist = [self.__wrap( x ) for x in initlist]
		super(PersistentExternalizableWeakList,self).__init__(initlist)


	def __getitem__(self, i ):
		return super(PersistentExternalizableWeakList,self).__getitem__( i )()

	# NOTE: __iter__ is implemented with __getitem__ so we don't reimplement.
	# However, __eq__ isn't, it wants to directly compare lists
	def __eq__( self, other ):
		# If we just compare lists, weak refs will fail badly
		# if they're compared with non-weak refs
		if not isinstance( other, collections.Sequence ):
			return False

		result = False
		if len(self) == len(other):
			result = True
			for i in xrange(len(self)):
				if self[i] != other[i]:
					result = False
					break
		return result

	def __wrap( self, obj ):
		return obj if isinstance( obj, PWeakRef ) else PWeakRef( obj )


	def remove(self,value):
		super(PersistentExternalizableWeakList,self).remove( self.__wrap( PWeakRef(value) ) )


	def __setitem__(self, i, item):
		super(PersistentExternalizableWeakList,self).__setitem__( i, self.__wrap( PWeakRef( item ) ) )


	def __setslice__(self, i, j, other):
		raise TypeError( 'Not supported' ) # pragma: no cover

	# Unfortunately, these are not implemented in terms of the primitives, so
	# we need to overide each one. They can throw exceptions, so we're careful
	# not to prematurely update lastMod

	def __iadd__(self, other):
		# We must wrap each element in a weak ref
		# Note that the builtin list only accepts other lists,
		# but the UserList from which we are descended accepts
		# any iterable.
		result = super(PersistentExternalizableWeakList,self).__iadd__([self.__wrap(PWeakRef(o)) for o in other])

		return result

	def __imul__(self, n):
		result = super(PersistentExternalizableWeakList,self).__imul__(n)

		return result

	def append(self, item):
		super(PersistentExternalizableWeakList,self).append(self.__wrap( PWeakRef(item) ) )


	def insert(self, i, item):
		super(PersistentExternalizableWeakList,self).insert( i, self.__wrap( PWeakRef(item)) )


	def pop(self, i=-1):
		rtn = super(PersistentExternalizableWeakList,self).pop( i )

		return rtn()

	def extend(self, other):
		for x in other: self.append( x )

	def count( self, item ):
		return super(PersistentExternalizableWeakList,self).count( self.__wrap( PWeakRef( item ) ) )

	def index( self, item, *args ):
		return super(PersistentExternalizableWeakList,self).index( self.__wrap( PWeakRef( item ) ), *args )
