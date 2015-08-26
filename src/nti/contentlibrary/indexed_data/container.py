#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Container implementations.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from zope.intid import IIntIds

from nti.common.property import Lazy

from nti.dublincore.time_mixins import PersistentCreatedAndModifiedTimeObject

from nti.zope_catalog.catalog import ResultSet

from .interfaces import IIndexedDataContainer
from .interfaces import IAudioIndexedDataContainer
from .interfaces import IVideoIndexedDataContainer
from .interfaces import ITimelineIndexedDataContainer
from .interfaces import ISlideDeckIndexedDataContainer
from .interfaces import IRelatedContentIndexedDataContainer

from . import get_catalog

from . import NTI_AUDIO_TYPE
from . import NTI_VIDEO_TYPE
from . import NTI_TIMELINE_TYPE
from . import NTI_SLIDE_DECK_TYPE
from . import NTI_RELATED_WORK_REF_TYPE

@interface.implementer(IIndexedDataContainer)
class IndexedDataContainer(PersistentCreatedAndModifiedTimeObject): 
	# Make it persistent for BWC

	type = None
	
	__name__ = None
	__parent__ = None
	
	def __init__(self, unit):
		self.ntiid = getattr(unit, 'ntiid', None) or getattr(unit, 'NTIID', None) or u''

	@Lazy
	def catalog(self):
		return get_catalog()

	@Lazy
	def intids(self):
		return component.getUtility(IIntIds)

	def __getitem__(self, key):
		items = list(self.catalog.search_objects(container_ntiids=(self.ntiid,),
												 provided=self.type,
												 ntiid=key,
												 intids=self.intids))
		if len(items) == 1:
			return items[0]
		else:
			raise KeyError(key)

	def get(self, key, default=None):
		try:
			return self[key]
		except KeyError:
			return default

	def __contains__(self, key):
		items = self.catalog.get_references(container_ntiids=(self.ntiid,),
											provided=self.type,
											ntiid=key)
		return len(items) == 1
	contains_data_item_with_ntiid = __contains__

	@property
	def doc_ids(self):
		result = self.catalog.get_references(container_ntiids=(self.ntiid,),
											 provided=self.type)
		return result

	def keys(self):
		ntiid_index = self.catalog.ntiid_index
		for doc_id in self.doc_ids:
			value = ntiid_index.documents_to_values.get(doc_id)
			if value is not None:
				yield value

	def __iter__(self):
		return iter(self.keys())

	def values(self):
		for obj in ResultSet(self.doc_ids, self.intids, True):
			yield obj
	get_data_items = values

	def items(self):
		for doc_id, value in ResultSet(self.doc_ids, self.intids, True).iter_pairs():
			return doc_id, value

	def __len__(self):
		return len(self.doc_ids)

@interface.implementer(IAudioIndexedDataContainer)
class AudioIndexedDataContainer(IndexedDataContainer):
	type = NTI_AUDIO_TYPE

@interface.implementer(IVideoIndexedDataContainer)
class VideoIndexedDataContainer(IndexedDataContainer):
	type = NTI_VIDEO_TYPE

@interface.implementer(IRelatedContentIndexedDataContainer)
class RelatedContentIndexedDataContainer(IndexedDataContainer):
	type = NTI_RELATED_WORK_REF_TYPE

@interface.implementer(ITimelineIndexedDataContainer)
class TimelineIndexedDataContainer(IndexedDataContainer):
	type = NTI_TIMELINE_TYPE

@interface.implementer(ISlideDeckIndexedDataContainer)
class SlideDeckIndexedDataContainer(IndexedDataContainer):
	type = NTI_SLIDE_DECK_TYPE

from zope.deprecation import deprecated

from zope.container.contained import Contained

from zc.dict import Dict

deprecated('_IndexedDataDict', 'No longer used')
class _IndexedDataDict(Dict, Contained):
	pass
