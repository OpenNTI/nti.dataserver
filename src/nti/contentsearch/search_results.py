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
from nti.contentsearch.interfaces import ISearchResultsList
from nti.contentsearch.interfaces import ISearchHitPredicate
from nti.contentsearch.interfaces import ISearchHitComparator
from nti.contentsearch.interfaces import ISearchHitComparatorFactory

from nti.property.property import alias

from nti.schema.field import SchemaConfigured

from nti.schema.fieldproperty import createDirectFieldProperties

def get_search_hit_predicate(item):
	predicates = list(component.subscribers((item,), ISearchHitPredicate))
	def uber_filter(item, score):
		return all((p.allow(item, score) for p in predicates))
	return uber_filter

def is_hit_allowed(item, score=1.0, query=None):
	score = score or 1.0
	predicate = get_search_hit_predicate(item)
	return predicate(item, score, query)

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
	Name = name = alias('__name__')

	def __init__(self, *args, **kwargs):
		super(SearchResultsMixin, self).__init__(*args, **kwargs)

	def __repr__(self):
		return '%s(hits=%s)' % (self.__class__.__name__, len(self))
	__str__ = __repr__

	@property
	def Hits(self):
		return ()

	def __len__(self):
		return len(self.Hits)

	def __iter__(self):
		return iter(self.Hits)

@interface.implementer(ISearchResults, IContentTypeAware)
class SearchResults(SearchResultsMixin, SchemaConfigured):
	createDirectFieldProperties(ISearchResults)

	mime_type = mimeType = u"application/vnd.nextthought.search.searchresults"
	
	_hits = ()
	_count = 0
	_sorted = False
	HitMetaData = None

	total = alias('NumFound')
	metadata = alias('HitMetaData')

	def __init__(self, *args, **kwargs):
		super(SearchResults, self).__init__(*args, **kwargs)
		self._count = 0
		self._hits = []
		self._seen = set()
		self.HitMetaData = SearchHitMetaData()

	def _raw_hits(self):
		return self._hits

	def _get_hits(self):
		if not self._sorted:
			self.sort()
		return self._hits
	def _set_hits(self, hits):
		for hit in hits or ():
			self._add_hit(hit)
	Hits = hits = property(_get_hits, _set_hits)

	def _get_lastModified(self):
		return self.HitMetaData.lastModified if self.HitMetaData else 0
	def _set_lastModified(self, v):
		pass
	lastModified = property(_get_lastModified, _set_lastModified)

	def _get_createdTime(self):
		return self.HitMetaData.createdTime if self.HitMetaData else 0
	def _set_createdTime(self, v):
		pass
	createdTime = property(_get_createdTime, _set_createdTime)

	@property
	def _limit(self):
		return getattr(self.query, 'limit', None) or sys.maxint

	def _add_hit(self, hit):
		if hit.ID not in self._seen and self._count < self._limit:
			self._count += 1
			self._sorted = False
			self._hits.append(hit)
			self._seen.add(hit.ID)
			return True
		return False

	def _add(self, hit):
		if True or is_hit_allowed(hit.Target, hit.Score, self.Query):
			if self._add_hit(hit):
				self.metadata.track(hit)
				return True
		else:
			self.metadata.filtered_count += 1
		return False

	def add(self, hit):
		self._add(hit)

	def extend(self, items):
		for item in items or ():
			self._add(item)

	def sort(self, sortOn=None):
		sortOn = sortOn or (self.query.sortOn if self.query else u'')
		factory = component.queryUtility(ISearchHitComparatorFactory, name=sortOn)
		comparator = factory(self) if factory is not None else None
		if comparator is not None:
			self._sorted = True
			reverse = not self.query.is_descending_sort_order
			self._hits.sort(comparator.compare, reverse=reverse)

	def __len__(self):
		return self._count

	def __iadd__(self, other):
		if ISearchResults.providedBy(other):
			self._set_hits(other._raw_hits())
			self.HitMetaData += other.HitMetaData
		return self

@interface.implementer(ISuggestResults, IContentTypeAware)
class SuggestResults(SearchResultsMixin, SchemaConfigured):
	createDirectFieldProperties(ISearchResults)

	mime_type = mimeType = u"application/vnd.nextthought.search.suggestresults"

	_words = ()

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

@interface.implementer(ISearchResultsList, IContentTypeAware)
class SearchResultsList(SchemaConfigured):
	createDirectFieldProperties(ISearchResultsList)

	mime_type = mimeType = u"application/vnd.nextthought.search.searchresultslist"
	
	_items = None

	def _get_items(self):
		return self._items or ()
	def _set_items(self, items):
		self._items = items
	items = Items = property(_get_items, _set_items)

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
