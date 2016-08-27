#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Search results

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

from zope.location.interfaces import ISublocations

from zope.mimetype.interfaces import IContentTypeAware

from nti.common.iterables import isorted

from nti.property.property import alias

from .common import get_mimetype_from_type

from .constants import VIDEO_TRANSCRIPT_MIME_TYPE

from .search_hits import get_search_hit

from .interfaces import ISearchQuery
from .interfaces import ITypeResolver
from .interfaces import INTIIDResolver
from .interfaces import ISearchResults
from .interfaces import ISuggestResults
from .interfaces import IContentSearchHit
from .interfaces import ISearchHitMetaData
from .interfaces import IUserDataSearchHit
from .interfaces import ISearchHitPredicate
from .interfaces import IContainerIDResolver
from .interfaces import ISearchHitComparator
from .interfaces import ILastModifiedResolver
from .interfaces import ISearchResultsCreator
from .interfaces import ISuggestResultsCreator
from .interfaces import ISuggestAndSearchResults
from .interfaces import ISearchHitComparatorFactory
from .interfaces import ISuggestAndSearchResultsCreator

create_search_hit = get_search_hit  # alias

def _lookup_subscribers(subscriptions=()):
	result = []
	for subscription in subscriptions:
		subscriber = subscription()  # construct w/ passing any item
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

	def track(self, selected):
		self.SearchTime = time.time() - self._ref

		resolver = ITypeResolver(selected, None)
		name = getattr(resolver, 'type', u'')
		isVideo = get_mimetype_from_type(name) == VIDEO_TRANSCRIPT_MIME_TYPE

		# container count
		if isVideo:  # a video it's its own container
			resolver = INTIIDResolver(selected, None)
			containerId = resolver.ntiid if resolver else self.unspecified_container
		else:
			resolver = IContainerIDResolver(selected, None)
			containerId = resolver.containerId if resolver else self.unspecified_container
		self.container_count[containerId] = self.container_count[containerId] + 1

		# last modified
		resolver = ILastModifiedResolver(selected, None)
		lastModified = resolver.lastModified if resolver else 0
		self.lastModified = max(self.lastModified, lastModified or 0)

		# type count
		resolver = ITypeResolver(selected, None)
		type_name = resolver.type if resolver else u'unknown'
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

class _MetaSearchResults(type):

	def __new__(cls, name, bases, dct):
		t = type.__new__(cls, name, bases, dct)
		t.mime_type = t.mimeType = u"application/vnd.nextthought.search.%s" % name[1:].lower()
		setattr(t, '__external_can_create__', True)
		setattr(t, '__external_class_name__', name[1:])
		t.parameters = dict()
		return t

class _BaseSearchResults(Contained):

	sorted = False

	Query = alias('query')

	def __init__(self, query=None):
		super(_BaseSearchResults, self).__init__()
		self.query = ISearchQuery(query, None)

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

@interface.implementer(ISublocations,
					   ISearchResults,
					   IContentTypeAware)
class _SearchResults(_BaseSearchResults):

	__metaclass__ = _MetaSearchResults

	metadata = alias('HitMetaData')

	def __init__(self, query=None):
		super(_SearchResults, self).__init__(query)
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
	def ContentHits(self):
		for hit in self._raw_hits():
			if IContentSearchHit.providedBy(hit):
				yield hit

	@property
	def UserDataHits(self):
		for hit in self._raw_hits():
			if IUserDataSearchHit.providedBy(hit):
				yield hit

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
		if hit.OID not in self._seen and self.count < self._limit:
			self.count += 1
			self.sorted = False
			self._hits.append(hit)
			self._seen.add(hit.OID)
			return True
		return False

	def _add(self, item, score=1.0):
		if isinstance(item, (list, tuple)):
			item, score = item[0], item[1]

		if _allow_search_hit(self._filterCache, item, score, self.Query):
			hit = create_search_hit(item, score, self.Query)
			if self._add_hit(hit):
				self.metadata.track(item)
			else:
				del hit
		else:
			self.metadata.filtered_count += 1

	def add(self, hit, score=1.0):
		self._add(hit, score)

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

	def sublocations(self):
		for hit in self._raw_hits():
			yield hit

	def __len__(self):
		return self.count

	def __iadd__(self, other):
		if 	ISearchResults.providedBy(other) or \
			ISuggestAndSearchResults.providedBy(other):

			self._set_hits(other._raw_hits())
			self.HitMetaData += other.HitMetaData

		return self

	def __getstate__(self):
		return {k: v for
				k, v in self.__dict__.iteritems()
				if not k.startswith('_v')}

	def __setstate__(self, state):
		self_dict = self.__dict__
		for k, v in state.iteritems():
			if not k.startswith('_v'):
				self_dict[str(k)] = v
		self._v_filterCache = None

@interface.implementer(ISuggestResults, IContentTypeAware)
class _SuggestResults(_BaseSearchResults):

	__metaclass__ = _MetaSearchResults

	lastModified = createdTime = 0

	def __init__(self, query=None):
		super(_SuggestResults, self).__init__(query)
		self._words = set()

	def _get_words(self):
		return sorted(self._words)
	def _set_words(self, words):
		self._words.update(words or ())
	suggestions = Suggestions = Hits = hits = property(_get_words, _set_words)

	def add_suggestions(self, items):
		items = (items,) if isinstance(items, six.string_types) or \
						 not isinstance(items, collections.Iterable) else items
		self._extend(items)  # avoid any possible conflict w/ _SuggestAndSearchResults

	add = add_suggestions

	def _extend(self, items):
		for item in items or ():
			self._words.add(unicode(item))
	extend = _extend

	def __iadd__(self, other):
		if 	ISuggestResults.providedBy(other) or \
			ISuggestAndSearchResults.providedBy(other):
			self._words.update(other.suggestions)
		return self

@interface.implementer(ISuggestAndSearchResults)
class _SuggestAndSearchResults(_SearchResults, _SuggestResults):

	__metaclass__ = _MetaSearchResults

	def __init__(self, query=None):
		_SearchResults.__init__(self, query)
		_SuggestResults.__init__(self, query)

	Hits = hits = property(_SearchResults._get_hits, _SearchResults._set_hits)
	suggestions = Suggestions = property(_SuggestResults._get_words,
										 _SuggestResults._set_words)

	def clone(self, meta=True, hits=False, suggestions=True):
		result = _SearchResults.clone(self, meta, hits)
		if suggestions:
			result.Suggestions = self.Suggestions
		return result

	def add(self, item, score=1.0):
		_SearchResults.add(self, item, score)

	def extend(self, items):
		_SearchResults.extend(self, items)

	def __iadd__(self, other):
		_SearchResults.__iadd__(self, other)
		_SuggestResults.__iadd__(self, other)
		return self

@interface.implementer(ISearchResultsCreator)
class _SearchResultCreator(object):

	def __call__(self, query=None):
		return _SearchResults(query)

@interface.implementer(ISuggestResultsCreator)
class _SuggestResultsCreator(object):

	def __call__(self, query=None):
		return _SuggestResults(query)

@interface.implementer(ISuggestAndSearchResultsCreator)
class _SuggestAndSearchResultsCreator(object):

	def __call__(self, query=None):
		return _SuggestAndSearchResults(query)

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
		iterator = reversed(hits) if reverse else iter(hits)
		return iterator

# legacy results

def empty_search_results(query):
	result = component.getUtility(ISearchResultsCreator)(query)
	return result

def get_or_create_search_results(query, store=None):
	results = store if store is not None else empty_search_results(query)
	return results

def empty_suggest_and_search_results(query):
	result = component.getUtility(ISuggestAndSearchResultsCreator)(query)
	return result

def get_or_create_suggest_and_search_results(query, store=None):
	results = store if store is not None else empty_suggest_and_search_results(query)
	return results

def empty_suggest_results(query):
	result = component.getUtility(ISuggestResultsCreator)(query)
	return result

def get_or_create_suggest_results(query, store=None):
	results = store if store is not None else empty_suggest_results(query)
	return results

def _preflight(a, b):
	if a is None and b is None:
		result = (None, True)
	elif a is None and b is not None:
		result = (b, True)
	elif a is not None and b is None:
		result = (a, True)
	elif a is b:
		result = (a, True)
	else:
		result = (None, False)
	return result

def _merge(a, b):
	a += b
	for k, vb in b.__dict__.items():
		if not k.startswith('_') and k not in a.__dict__:
			a.__dict__[k] = vb
	return a

def merge_search_results(a, b):
	v, t = _preflight(a, b)
	if t: return v
	return _merge(a, b)

def merge_suggest_and_search_results(a, b):
	v, t = _preflight(a, b)
	if t: return v
	return _merge(a, b)

def merge_suggest_results(a, b):
	v, t = _preflight(a, b)
	if t: return v
	return _merge(a, b)
