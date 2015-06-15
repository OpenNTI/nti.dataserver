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

from nti.common.property import Lazy

from .interfaces import IIndexedDataContainer
from .interfaces import IAudioIndexedDataContainer
from .interfaces import IVideoIndexedDataContainer
from .interfaces import ITimelineIndexedDataContainer
from .interfaces import ISlideDeckIndexedDataContainer
from .interfaces import IRelatedContentIndexedDataContainer

from . import get_catalog

@interface.implementer(IIndexedDataContainer)
class IndexedDataContainer(object):

	def __init__(self, ntiid):
		self.ntiid = ntiid

	@Lazy
	def catalog(self):
		return get_catalog()

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
