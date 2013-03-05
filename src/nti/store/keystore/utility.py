# -*- coding: utf-8 -*-
"""
Implementation of the :class:`.interfaces.IKeyStore` utility.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import persistent

from zope import interface
from zope.container import contained
from zope.container.btree import BTreeContainer

from zope.annotation import interfaces as an_interfaces
from zope.location import interfaces as loc_interfaces

from . import interfaces as ks_interfaces

@interface.implementer(ks_interfaces.IKeyStore,
					   an_interfaces.IAttributeAnnotatable,
					   loc_interfaces.ISublocations)
class PersistentKeyStore(persistent.Persistent, contained.Contained):
	"""
	Basic implementation of keystore.
	"""

	def __init__(self):
		self._keys = BTreeContainer()
		contained.contained( self._keys, self, '_keys' )

	def sublocations(self):
		yield self._keys
		annotations = an_interfaces.IAnnotations(self, {})
		for val in annotations.values():
			if getattr( val, '__parent__', None ) is self: #pragma: no cover
				yield val

	def registerKey(self, key):
		if not key.alias:
			raise KeyError('Key must already have an alias')
		self._keys[key.alias] = key

	def getKeyByAlias( self, alias ):
		return self._keys.get( alias )

class ZcmlKeyStore(PersistentKeyStore):
	pass
