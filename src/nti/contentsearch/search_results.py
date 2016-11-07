#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six
import sys
import time
import collections

from zope import component
from zope import interface

from zope.container.contained import Contained

from zope.mimetype.interfaces import IContentTypeAware

from nti.common.iterables import isorted
from nti.common.string import to_unicode

from nti.contentsearch.interfaces import ISearchResults
from nti.contentsearch.interfaces import ISuggestResults
from nti.contentsearch.interfaces import ISearchHitMetaData
from nti.contentsearch.interfaces import ISearchHitPredicate
from nti.contentsearch.interfaces import ISearchHitComparator
from nti.contentsearch.interfaces import ISearchHitComparatorFactory

from nti.property.property import alias

from nti.schema.field import SchemaConfigured

from nti.schema.fieldproperty import createDirectFieldProperties

def _lookup_subscribers(subscriptions=()):
	result = []
	for subscription in subscriptions or ():
		subscriber = subscription()  # construct w/o passing any item
		if subscriber is not None:
			result.append(subscriber)
	return result

def _get_predicate(subscriptions=()):
	filters = _lookup_subscribers(subscriptions)
	if not filters:
		result = lambda *args, **kwargs:True
	else:
		def uber_filter(item, score=1.0, query=None):
			return all((f.allow(item, score, query) for f in filters))
		result = uber_filter
	return result

def _get_subscriptions(item, provided=ISearchHitPredicate):
	adapters = component.getSiteManager().adapters
	subscriptions = adapters.subscriptions([interface.providedBy(item)], provided)
	return tuple(subscriptions)

class _FilterCache(object):

	__slots__ = ('cache',)

	def __init__(self):
		self.cache = {}

	def _lookup(self, item):
		subscriptions = _get_subscriptions(item)
		predicate = self.cache.get(subscriptions, None)
		if predicate is None:
			predicate = _get_predicate(subscriptions)
			self.cache[subscriptions] = predicate
		return predicate

	def eval(self, item, score=1.0, query=None):
		predicate = self._lookup(item)
		__traceback_info__ = predicate
		return predicate(item, score, query)

def _allow_search_hit(filter_cache, item, score, query=None):
	result = filter_cache.eval(item, score, query)
	return result

@interface.implementer(ISearchHitMetaData)
class SearchHitMetaData(object):

	unspecified_container = u'+++unspecified_container+++'

	__external_can_create__ = True
	mime_type = mimeType = u"application/vnd.nextthought.search.searchhitmetadata"

	filtered_count = 0
	SearchTime = lastModified = createdTime = 0

	def __init__(self):
		self._ref = time.time()
		self.type_count = collections.defaultdict(int)
		self.container_count = collections.defaultdict(int)

	def _get_type_count(self):
		return dict(self.type_count)
	def _set_type_count(self, tc):
		self.type_count.update(tc or {})
	TypeCount = property(_get_type_count, _set_type_count)

	def _get_container_count(self):
		return dict(self.container_count)
	def _set_container_count(self, cc):
		self.container_count.update(cc or {})
	ContainerCount = property(_get_container_count, _set_container_count)

	@property
	def TotalHitCount(self):
		return sum(self.type_count.values())

	def _get_filtered_count(self):
		return self.filtered_count
	def _set_filtered_count(self, count):
		self.filtered_count = count
	FilteredCount = property(_get_filtered_count, _set_filtered_count)

	def track(self, hit):
		self.SearchTime = time.time() - self._ref

		# container count
		containers = hit.Containers or (self.unspecified_container,)
		for containerId in containers:
			self.container_count[containerId] = self.container_count[containerId] + 1

		lastModified = hit.lastModified or 0
		self.lastModified = max(self.lastModified, lastModified or 0)

		# type count
		type_name = hit.TargetMimeType or u'unknown'
		self.type_count[type_name] = self.type_count[type_name] + 1

	def __iadd__(self, other):
		# container count
		for k, v in other.container_count.items():
			self.container_count[k] = self.container_count[k] + v

		# last modified
		self.lastModified = max(self.lastModified, other.lastModified)

		# type count
		for k, v in other.type_count.items():
			self.type_count[k] = self.type_count[k] + v

		# search time
		self.SearchTime = max(self.SearchTime, other.SearchTime)

		return self

class SearchResultsMixin(Contained):

	sorted = False
	parameters = {}
	
	Query = alias('query')

	def __init__(self, *args, **kwargs):
		super(SearchResultsMixin, self).__init__(*args, **kwargs)

	def __repr__(self):
		return '%s(hits=%s)' % (self.__class__.__name__, len(self))
	__str__ = __repr__

	@property
	def Hits(self):
		raise NotImplementedError()

	def __len__(self):
		return len(self.Hits)

	def __iter__(self):
		return iter(self.Hits)

@interface.implementer(ISearchResults, IContentTypeAware)
class SearchResults(SchemaConfigured, SearchResultsMixin):
	createDirectFieldProperties(ISearchResults)

	mime_type = mimeType = u"application/vnd.nextthought.search.searchresults"
	
	metadata = alias('HitMetaData')

	def __init__(self, *args, **kwargs):
		super(SearchResults, self).__init__(*args, **kwargs)
		self.count = 0
		self._hits = []
		self._seen = set()
		self._v_filterCache = None
		self.HitMetaData = SearchHitMetaData()

	def clone(self, meta=True, hits=False):
		result = self.__class__()
		result.Query = self.Query
		if meta:
			result.HitMetaData += self.HitMetaData
		if hits:
			for hit in self._raw_hits():
				clone = hit.clone()
				result._add_hit(clone)
		return result

	def _raw_hits(self):
		return self._hits

	def _get_hits(self):
		if not self.sorted:
			self.sort()
		return self._hits
	def _set_hits(self, hits):
		for hit in hits or ():
			self._add_hit(hit)
	Hits = hits = property(_get_hits, _set_hits)

	@property
	def lastModified(self):
		return self.metadata.lastModified

	@property
	def createdTime(self):
		return self.metadata.createdTime

	@property
	def _limit(self):
		return getattr(self.query, 'limit', None) or sys.maxint

	@property
	def _filterCache(self):
		if self._v_filterCache is None:
			self._v_filterCache = _FilterCache()
		return self._v_filterCache

	def _add_hit(self, hit):
		if hit.ID not in self._seen and self.count < self._limit:
			self.count += 1
			self.sorted = False
			self._hits.append(hit)
			self._seen.add(hit.ID)
			return True
		return False

	def _add(self, hit):
		if _allow_search_hit(self._filterCache, hit, hit.Score, self.Query):
			if self._add_hit(hit):
				self.metadata.track(hit)
		else:
			self.metadata.filtered_count += 1

	def add(self, hit):
		self._add(hit)

	def extend(self, items):
		for item in items or ():
			self._add(item)

	def sort(self, sortOn=None):
		sortOn = sortOn or (self.query.sortOn if self.query else u'')
		factory = component.queryUtility(ISearchHitComparatorFactory,
										 name=sortOn)
		comparator = factory(self) if factory is not None else None
		if comparator is not None:
			self.sorted = True
			reverse = not self.query.is_descending_sort_order
			self._hits.sort(comparator.compare, reverse=reverse)

	def __len__(self):
		return self.count

	def __iadd__(self, other):
		if ISearchResults.providedBy(other):
			self._set_hits(other._raw_hits())
			self.HitMetaData += other.HitMetaData
		return self

@interface.implementer(ISuggestResults, IContentTypeAware)
class SuggestResults(SchemaConfigured, SearchResultsMixin):
	createDirectFieldProperties(ISearchResults)

	mime_type = mimeType = u"application/vnd.nextthought.search.suggestresults"

	lastModified = createdTime = 0

	def __init__(self, *args, **kwargs):
		super(SuggestResults, self).__init__(*args, **kwargs)
		self._words = set()

	def _get_words(self):
		return sorted(self._words)
	def _set_words(self, words):
		self._words.update(words or ())
	suggestions = Suggestions = Hits = hits = property(_get_words, _set_words)

	def add(self, item):
		if isinstance(item, six.string_types):
			item = item.split()
		self.extend(item)
	add_suggestions = add

	def extend(self, items):
		for item in items or ():
			self._words.add(to_unicode(item))

	def __iadd__(self, other):
		if ISuggestResults.providedBy(other):
			self._words.update(other.suggestions)
		return self

# sort

def sort_hits(hits, reverse=False, sortOn=None):
	comparator = component.queryUtility(ISearchHitComparator, name=sortOn) if sortOn else None
	if comparator is not None:
		if isinstance(hits, list):
			hits.sort(comparator.compare, reverse=reverse)
			return iter(hits)
		else:
			if reverse:
				comparator = lambda x, y: comparator(y, x)
			return isorted(hits, comparator)
	else:
		return reversed(hits) if reverse else iter(hits)
