#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Implementations of persistent dicts with various qualities.


$Id$
"""

from __future__ import print_function, unicode_literals

import time
import collections

from zope import interface

from . import interfaces
from .containers import _tx_key_insen

from nti.zodb.persistentproperty import PersistentPropertyHolder
from nti.zodb.minmax import NumericMaximum, NumericPropertyDefaultingToZero

import zc.dict

@interface.implementer(interfaces.ILastModified)
class LastModifiedDict(PersistentPropertyHolder,zc.dict.Dict):
	"""
	A BTree-based persistent dictionary that maintains the
	data required by :class:`interfaces.ILastModified`. Since this is not a
	:class:`zope.container.interfaces.IContainer`, this is done when this object is modified.
	"""

	lastModified = NumericPropertyDefaultingToZero('_lastModified', NumericMaximum, as_number=True )

	def __init__( self, *args, **kwargs ):
		self.createdTime = time.time()
		super(LastModifiedDict,self).__init__( *args, **kwargs )

	def updateLastMod(self, t=None ):
		self.lastModified = t if t is not None and t > self.lastModified else time.time()
		return self.lastModified

	def updateLastModIfGreater( self, t ):
		"Only if the given time is (not None and) greater than this object's is this object's time changed."
		if t is not None and t > self.lastModified:
			self.lastModified = t
		return self.lastModified

	def pop(self, key, *args ):
		try:
			result = super(LastModifiedDict,self).pop( key )
			self.updateLastMod()
			return result
		except KeyError:
			if args:
				return args[0]
			raise

	def clear(self):
		len_ = self._len()
		if len_:
			super(LastModifiedDict,self).clear()
			self.updateLastMod()

	def __setitem__( self, key, value ):
		super(LastModifiedDict,self).__setitem__( key, value )
		self.updateLastMod()

collections.Mapping.register(zc.dict.Dict)


class CaseInsensitiveLastModifiedDict(LastModifiedDict):
	"""
	Preserves the case of keys but compares them case-insensitively.
	"""

	# First the documented mutation methods
	def pop( self, key, *args ):
		LastModifiedDict.pop( self, _tx_key_insen(key), *args )

	def __setitem__( self, key, value ):
		LastModifiedDict.__setitem__( self, _tx_key_insen(key), value )

	# Now the informational. Since these don't mutate, it's simplest
	# to go directly to the data member

	def __contains__( self, key ):
		return key is not None and self._data.__contains__( _tx_key_insen( key ) )

	def __iter__( self ):
		return iter( (k.key for k in self._data) )

	def __getitem__( self, key ):
		return self._data[_tx_key_insen(key)]

	def get( self, key, default=None ):
		if key is None: return default
		return self._data.get( _tx_key_insen( key ), default )

	def items( self, key=None ):
		if key is not None:
			key = _tx_key_insen( key )

		return ((k.key, v) for k, v in self._data.items(key))

	def keys(self, key=None ):
		if key is not None:
			key = _tx_key_insen( key )
		return (k.key for k in self._data.keys(key))

	def values( self, key=None ):
		if key is not None:
			key = _tx_key_insen( key )
		return (v for v in self._data.values(key))

	iteritems = items
	iterkeys = keys
	itervalues = values
	has_key = __contains__
