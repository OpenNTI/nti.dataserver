#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Container implementations.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from zope.cachedescriptors.property import Lazy

from zc.dict import Dict

from nti.dublincore.time_mixins import PersistentCreatedAndModifiedTimeObject

from .interfaces import IAudioIndexedDataContainer
from .interfaces import IVideoIndexedDataContainer
from .interfaces import IWritableIndexedDataContainer
from .interfaces import ITimelineIndexedDataContainer
from .interfaces import ISlideDeckIndexedDataContainer
from .interfaces import IRelatedContentIndexedDataContainer

class _IndexedDataDict(Dict):
	__parent__ = None
	__name__ = None

@interface.implementer(IWritableIndexedDataContainer)
class IndexedDataContainer(PersistentCreatedAndModifiedTimeObject):

	__parent__ = None
	__name__ = None

	def __init__(self, ntiid):
		super(IndexedDataContainer, self).__init__()
		self.ntiid = ntiid
		# Override the super and do not set lastModified
		# to current time because we will want to track it
		# externally; instead, set it to the default for
		# "unknown"
		self.lastModified = -1

	@Lazy
	def _data(self):
		data = _IndexedDataDict()
		data.__parent__ = self
		self._p_changed = True
		return data

	def set_data_items(self, data_items):
		self._p_activate()

		if '_data' in self.__dict__:
			self._data.clear()

		data = self._data
		for item in data_items or ():
			ntiid = item.get('ntiid') or item.get('NTIID')
			if ntiid:
				data[ntiid] = item

	def __getitem__(self, key):
		self._p_activate()
		if '_data' in self.__dict__:
			return self._data[key]
		else:
			raise KeyError(key)

	def get(self, key, default=None):
		try:
			return self[key]
		except KeyError:
			return default

	def __contains__(self, ntiid):
		self._p_activate()
		return '_data' in self.__dict__ and ntiid in self._data
	contains_data_item_with_ntiid = __contains__

	def keys(self):
		self._p_activate()
		if '_data' in self.__dict__:
			return self._data.keys()
		return ()

	def __iter__(self):
		return iter(self.keys())

	def values(self):
		self._p_activate()
		if '_data' in self.__dict__:
			return self._data.values()
		return ()
	get_data_items = values

	def items(self):
		self._p_activate()
		if '_data' in self.__dict__:
			return self._data.items()
		return ()

	def __len__(self):
		self._p_activate()
		if '_data' in self.__dict__:
			return len(self._data)
		return 0

@interface.implementer(IAudioIndexedDataContainer)
class AudioIndexedDataContainer(IndexedDataContainer):
	pass

@interface.implementer(IVideoIndexedDataContainer)
class VideoIndexedDataContainer(IndexedDataContainer):
	pass

@interface.implementer(IRelatedContentIndexedDataContainer)
class RelatedContentIndexedDataContainer(IndexedDataContainer):
	pass

@interface.implementer(ITimelineIndexedDataContainer)
class TimelineIndexedDataContainer(IndexedDataContainer):
	pass

@interface.implementer(ISlideDeckIndexedDataContainer)
class SlideDeckIndexedDataContainer(IndexedDataContainer):
	pass
