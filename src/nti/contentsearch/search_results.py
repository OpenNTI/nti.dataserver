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

from zope import interface
from zope import component
from zope.location.interfaces import ISublocations
from zope.container import contained as zcontained
from zope.mimetype import interfaces as zmime_interfaces

from nti.mimetype.mimetype import nti_mimetype_with_class

from nti.utils.sort import isorted
from nti.utils.property import Lazy, alias

from . import common
from . import constants
from . import search_hits
from . import interfaces as search_interfaces

create_search_hit = search_hits.get_search_hit  # alias

def _lookup_subscribers(subscriptions=()):
	result = []
	for subscription in subscriptions:
		subscriber = subscription() # construct w/ passing any item
		if subscriber is not None:
			result.append(subscriber)
	return result

def _get_predicate(subscriptions=()):
	filters = _lookup_subscribers(subscriptions)
	if not filters:
		result = lambda *args:True
	else:
		def uber_filter(item, score=1.0):
			return all((f.allow(item, score) for f in filters))
		result = uber_filter
	return result
	
def _get_subscriptions(item, provided=search_interfaces.ISearchHitPredicate):
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
		
	def eval(self, item, score=1.0):
		predicate = self._lookup(item)
		return predicate(item, score)

def _allow_search_hit(filter_cache, item, score):
	result = filter_cache.eval(item, score)
	return result

@interface.implementer(search_interfaces.ISearchHitMetaData)
class SearchHitMetaData(object):

	unspecified_container = u'+++unspecified_container+++'

	__external_can_create__ = True
	mime_type = mimeType = nti_mimetype_with_class('SearchHitMetaData')

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

		resolver = search_interfaces.ITypeResolver(selected, None)
		name = getattr(resolver, 'type', u'')
		isVideo = common.get_mimetype_from_type(name) == constants.VIDEO_TRANSCRIPT_MIME_TYPE

		# container count
		if isVideo:  # a video it's its own container
			resolver = search_interfaces.INTIIDResolver(selected, None)
			containerId = resolver.ntiid if resolver else self.unspecified_container
		else:
			resolver = search_interfaces.IContainerIDResolver(selected, None)
			containerId = resolver.containerId if resolver else self.unspecified_container
		self.container_count[containerId] = self.container_count[containerId] + 1

		# last modified
		resolver = search_interfaces.ILastModifiedResolver(selected, None)
		lastModified = resolver.lastModified if resolver else 0
		self.lastModified = max(self.lastModified, lastModified or 0)

		# type count
		resolver = search_interfaces.ITypeResolver(selected, None)
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
		t.mime_type = t.mimeType = nti_mimetype_with_class(name[1:].lower())
		setattr(t, '__external_can_create__', True)
		setattr(t, '__external_class_name__', name[1:])
		t.parameters = dict()
		return t

class _BaseSearchResults(zcontained.Contained):

	sorted = False

	Query = alias('query')

	def __init__(self, query=None):
		super(_BaseSearchResults,self).__init__()
		self.query = search_interfaces.ISearchQuery(query, None)

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
					   search_interfaces.ISearchResults,
					   zmime_interfaces.IContentTypeAware)
class _SearchResults(_BaseSearchResults):

	__metaclass__ = _MetaSearchResults

	metadata = alias('HitMetaData')

	def __init__(self, query=None):
		super(_SearchResults, self).__init__(query)
		self.count = 0
		self._hits = []
		self._seen = set()
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
			if search_interfaces.IContentSearchHit.providedBy(hit):
				yield hit

	@property
	def UserDataHits(self):
		for hit in self._raw_hits():
			if search_interfaces.IUserDataSearchHit.providedBy(hit):
				yield hit

	@property
	def lastModified(self):
		return self.metadata.lastModified

	@property
	def createdTime(self):
		return self.metadata.createdTime

	@Lazy
	def _limit(self):
		return getattr(self.query, 'limit', None) or sys.maxint

	@Lazy
	def _filterCache(self):
		return _FilterCache()

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

		if _allow_search_hit(self._filterCache, item, score):
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
		factory = component.queryUtility(search_interfaces.ISearchHitComparatorFactory,
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
		if 	search_interfaces.ISearchResults.providedBy(other) or \
			search_interfaces.ISuggestAndSearchResults.providedBy(other):

			self._set_hits(other._raw_hits())
			self.HitMetaData += other.HitMetaData

		return self

@interface.implementer(search_interfaces.ISuggestResults,
					   zmime_interfaces.IContentTypeAware)
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
		if 	search_interfaces.ISuggestResults.providedBy(other) or \
			search_interfaces.ISuggestAndSearchResults.providedBy(other):
			self._words.update(other.suggestions)
		return self

@interface.implementer(search_interfaces.ISuggestAndSearchResults)
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

@interface.implementer(search_interfaces.ISearchResultsCreator)
class _SearchResultCreator(object):

	def __call__(self, query=None):
		return _SearchResults(query)

@interface.implementer(search_interfaces.ISuggestResultsCreator)
class _SuggestResultsCreator(object):

	def __call__(self, query=None):
		return _SuggestResults(query)

@interface.implementer(search_interfaces.ISuggestAndSearchResultsCreator)
class _SuggestAndSearchResultsCreator(object):

	def __call__(self, query=None):
		return _SuggestAndSearchResults(query)

# sort

def sort_hits(hits, reverse=False, sortOn=None):
	comparator = component.queryUtility(search_interfaces.ISearchHitComparator,
										name=sortOn) if sortOn else None
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
	result = component.getUtility(search_interfaces.ISearchResultsCreator)(query)
	return result

def get_or_create_search_results(query, store=None):
	results = store if store is not None else empty_search_results(query)
	return results

def empty_suggest_and_search_results(query):
	result = component.getUtility(
						search_interfaces.ISuggestAndSearchResultsCreator)(query)
	return result

def get_or_create_suggest_and_search_results(query, store=None):
	results = store if store is not None else empty_suggest_and_search_results(query)
	return results

def empty_suggest_results(query):
	result = component.getUtility(search_interfaces.ISuggestResultsCreator)(query)
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
