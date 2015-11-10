#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope.annotation.interfaces import IAttributeAnnotatable

from zope.component import getAdapter
from zope.component import queryAdapter

from zope.interface import implementer

from .ofs.interfaces import IOrderedContainer

from .lazy import LazyMap

from .interfaces import IOrdering
from .interfaces import IOrderableFolder
from .interfaces import IExplicitOrdering

from .btreefolder2 import _marker
from .btreefolder2 import BTreeFolder2Base

@implementer(IOrderedContainer, IOrderableFolder, IAttributeAnnotatable)
class OrderedBTreeFolderBase(BTreeFolder2Base):
	"""
	BTree folder base class with ordering support. The ordering
	is done by a named adapter (to IOrdering), which makes the policy
	changeable.
	"""

	_ordering = u''  # name of adapter defining ordering policy

	def __nonzero__(self):
		""" 
		a folder is something, even if it's empty 
		"""
		return True

	def getOrdering(self):
		""" 
		return the currently active ordering adapter for this folder 
		"""
		adapter = queryAdapter(self, IOrdering, name=self._ordering)
		if adapter is None:
			adapter = getAdapter(self, IOrdering)
		return adapter

	def setOrdering(self, ordering=u''):
		""" 
		(re)set ordering adapter to be used for this folder 
		"""
		if ordering:
			# make sure the adapter exists...
			getAdapter(self, IOrdering, name=ordering)
		self._ordering = ordering

	# IObjectManager

	def _getOb(self, uid, default=_marker):
		""" 
		Return the named object from the folder.
		"""
		try:
			return super(OrderedBTreeFolderBase, self)._getOb(uid, default)
		except KeyError, e:
			raise AttributeError(e)

	def _setOb(self, uid, obj):
		""" 
		Store the named object in the folder. 
		"""
		super(OrderedBTreeFolderBase, self)._setOb(uid, obj)
		self.getOrdering().notifyAdded(uid)  # notify the ordering adapter

	def _delOb(self, uid):
		""" 
		Remove the named object from the folder. 
		"""
		super(OrderedBTreeFolderBase, self)._delOb(uid)
		self.getOrdering().notifyRemoved(uid)  # notify the ordering adapter

	def objectIds(self, ordered=True):
		if not ordered:
			return super(OrderedBTreeFolderBase, self).objectIds()
		ordering = self.getOrdering()
		return ordering.idsInOrder()

	def objectValues(self):
		return LazyMap(self._getOb, self.objectIds())

	def objectItems(self):
		return LazyMap(lambda uid, _getOb=self._getOb: (uid, _getOb(id)),
					   self.objectIds())

	def getObjectPosition(self, uid):
		""" 
		Get the position of an object by its id. 
		"""
		return self.getOrdering().getObjectPosition(uid)

	def moveObjectsUp(self, ids, delta=1, subset_ids=None):
		""" 
		Move specified sub-objects up by delta in container. 
		"""
		ordering = self.getOrdering()
		if IExplicitOrdering.providedBy(ordering):
			return ordering.moveObjectsUp(ids, delta, subset_ids)
		else:
			return 0

	def moveObjectsDown(self, ids, delta=1, subset_ids=None):
		""" 
		Move specified sub-objects down by delta in container. 
		"""
		ordering = self.getOrdering()
		if IExplicitOrdering.providedBy(ordering):
			return ordering.moveObjectsDown(ids, delta, subset_ids)
		else:
			return 0

	def moveObjectsToTop(self, ids, subset_ids=None):
		""" 
		Move specified sub-objects to top of container. 
		"""
		ordering = self.getOrdering()
		if IExplicitOrdering.providedBy(ordering):
			return ordering.moveObjectsToTop(ids, subset_ids)
		else:
			return 0

	def moveObjectsToBottom(self, ids, subset_ids=None):
		""" 
		Move specified sub-objects to bottom of container.
		"""
		ordering = self.getOrdering()
		if IExplicitOrdering.providedBy(ordering):
			return ordering.moveObjectsToBottom(ids, subset_ids)
		else:
			return 0

	def moveObject(self, uid, position):
		""" 
		Move specified object to absolute position. 
		"""
		ordering = self.getOrdering()
		if IExplicitOrdering.providedBy(ordering):
			return ordering.moveObjectToPosition(uid, position)
		else:
			return 0

	def moveObjectToPosition(self, uid, position, suppress_events=False):
		""" 
		Move specified object to absolute position. 
		"""
		ordering = self.getOrdering()
		if IExplicitOrdering.providedBy(ordering):
			return ordering.moveObjectToPosition(uid, position, suppress_events)
		else:
			return 0

	def moveObjectsByDelta(self, ids, delta, subset_ids=None, suppress_events=False):
		""" 
		Move specified sub-objects by delta. 
		"""
		ordering = self.getOrdering()
		if IExplicitOrdering.providedBy(ordering):
			return ordering.moveObjectsByDelta(ids, delta, subset_ids, suppress_events)
		else:
			return 0

	def orderObjects(self, key=None, reverse=None):
		""" 
		Order sub-objects by key and direction. 
		"""
		ordering = self.getOrdering()
		if IExplicitOrdering.providedBy(ordering):
			return ordering.orderObjects(key, reverse)
		else:
			return 0

	def iterkeys(self):
		return iter(self.objectIds())

	def __setitem__(self, key, value):
		self._setObject(key, value)

	def __contains__(self, key):
		return key in self._tree

	def __delitem__(self, key):
		self._delObject(key)

	def __getitem__(self, key):
		value = self._getOb(key, None)
		if value is not None:
			return value
		raise KeyError(key)

	__iter__ = iterkeys
	keys = objectIds
	values = objectValues
	items = objectItems
