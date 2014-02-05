# -*- coding: utf-8 -*-
"""
Search results

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six
import collections

from gevent.local import local

from zope import interface
from zope import component
from zope.container import contained as zcontained
from zope.mimetype import interfaces as zmime_interfaces

from nti.mimetype.mimetype import nti_mimetype_with_class

from nti.utils.sort import isorted

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

class _FilterCache(local):

	def __init__(self):
		super(_FilterCache, self).__init__()
		self._cache = {}

	def _lookup(self, item):
		subscriptions = _get_subscriptions(item)
		predicate = self._cache.get(subscriptions, None)
		if predicate is None:
			predicate = _get_predicate(subscriptions)
			self._cache[subscriptions] = predicate
		return predicate
		
	def eval(self, item, score=1.0):
		predicate = self._lookup(item)
		return predicate(item, score)

_filter_cache = _FilterCache()
def allow_search_hit(item, score):
	result = _filter_cache.eval(item, score)
	return result

@interface.implementer(search_interfaces.ISearchHitMetaData)
class SearchHitMetaData(object):

	unspecified_container = u'+++unspecified_container+++'
	mime_type = mimeType = nti_mimetype_with_class('SearchHitMetaData')

	createdTime = lastModified = 0

	def __init__(self):
		self.type_count = collections.defaultdict(int)
		self.container_count = collections.defaultdict(int)

	@property
	def TotalHitCount(self):
		return sum(self.type_count.values())

	@property
	def TypeCount(self):
		return dict(self.type_count)

	@property
	def ContainerCount(self):
		return dict(self.container_count)

	def track(self, selected):
		# container count
		resolver = search_interfaces.IContainerIDResolver(selected, None)
		containerId = resolver.containerId if resolver else self.unspecified_container
		self.container_count[containerId] = self.container_count[containerId] + 1

		# last modified
		resolver = search_interfaces.ILastModifiedResolver(selected, None)
		lastModified = resolver.lastModified if resolver else 0
		self.lastModified = max(self.lastModified, lastModified or 0)

		# type count
		resolver = search_interfaces.ITypeResolver(selected, None)
		type_name = resolver.type if resolver else 0
		self.type_count[type_name] = self.type_count[type_name] + 1

	def __iadd__(self, other):
		# container count
		for k, v in other.container_count.items():
			self.container_count[k] = self.container_count[k] + v

		# last modified
		self.lastModified = max(self.lastModified, other.lastModified)

		# container count
		for k, v in other.type_count.items():
			self.type_count[k] = self.type_count[k] + v

		return self

class _MetaSearchResults(type):

	def __new__(cls, name, bases, dct):
		t = type.__new__(cls, name, bases, dct)
		t.mime_type = t.mimeType = nti_mimetype_with_class(name[1:].lower())
		t.parameters = dict()
		return t

class _BaseSearchResults(zcontained.Contained):

	sorted = False

	def __init__(self, query):
		super(_BaseSearchResults,self).__init__()
		self.query = search_interfaces.ISearchQuery(query)

	def __str__(self):
		return self.__repr__()

	def __repr__(self):
		return '%s(hits=%s)' % (self.__class__.__name__, self.total)

	@property
	def Query(self):
		return self.query

	@property
	def hits(self):
		raise NotImplementedError()

	@property
	def total(self):
		return len(self.hits)

	def __len__(self):
		return len(self.hits)

	def __iter__(self):
		return iter(self.hits)

@interface.implementer(search_interfaces.ISearchResults,
					   zmime_interfaces.IContentTypeAware)
class _SearchResults(_BaseSearchResults):

	__metaclass__ = _MetaSearchResults

	createdTime = lastModified = 0

	def __init__(self, query):
		super(_SearchResults, self).__init__(query)
		self._hits = []
		self._ihitmeta = SearchHitMetaData()

	@property
	def hits(self):
		return self._hits

	@property
	def metadata(self):
		return self._ihitmeta

	def _add(self, item, score=1.0):
		if isinstance(item, (list, tuple)):
			item, score = item[0], item[1]

		if allow_search_hit(item, score):
			self.sorted = False
			hit = create_search_hit(item, score, self.Query, self)
			self._hits.append(hit)
			self._ihitmeta.track(item)

	def add(self, hit, score=1.0):
		self._add(hit, score)

	def extend(self, items):
		for item in items or ():
			self._add(item)

	def sort(self, sortOn=None):
		sortOn = sortOn or self.query.sortOn
		comparator = component.queryUtility(search_interfaces.ISearchHitComparator,
											name=sortOn)
		if comparator is not None:
			self.sorted = True
			reverse = not self.query.is_descending_sort_order
			self._hits.sort(comparator.compare, reverse=reverse)

	def __iadd__(self, other):
		if 	search_interfaces.ISearchResults.providedBy(other) or \
			search_interfaces.ISuggestAndSearchResults.providedBy(other):

			self.sorted = False
			self._hits.extend(other.hits)
			self._ihitmeta += other._ihitmeta

		return self

@interface.implementer(search_interfaces.ISuggestResults,
					   zmime_interfaces.IContentTypeAware)
class _SuggestResults(_BaseSearchResults):

	__metaclass__ = _MetaSearchResults

	def __init__(self, query):
		super(_SuggestResults, self).__init__(query)
		self._words = set()

	def get_hits(self):
		"""
		The suggested words, sorted alphabetically. Immutable.
		"""
		return sorted(self._words)

	hits = property(get_hits)
	suggestions = hits

	def add_suggestions(self, items):
		items = [items] if isinstance(items, six.string_types) or \
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

	def __init__(self, query):
		_SearchResults.__init__(self, query)
		_SuggestResults.__init__(self, query)

	def get_hits(self):
		return self._hits

	hits = property(get_hits)

	def get_words(self):
		"""
		The suggested words, sorted alphabetically. Immutable.
		"""
		return sorted(self._words)

	suggestions = property(get_words)

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

	def __call__(self, query):
		return _SearchResults(query)

@interface.implementer(search_interfaces.ISuggestResultsCreator)
class _SuggestResultsCreator(object):

	def __call__(self, query):
		return _SuggestResults(query)

@interface.implementer(search_interfaces.ISuggestAndSearchResultsCreator)
class _SuggestAndSearchResultsCreator(object):

	def __call__(self, query):
		return _SuggestAndSearchResults(query)

# sort

def sort_hits(hits, reverse=False, sortOn=None):
	comparator = component.queryUtility(search_interfaces.ISearchHitComparator,
										name=sortOn) if sortOn else None
	if comparator is not None:
		if reverse:
			comparator = lambda x, y: comparator(y, x)
		return isorted(hits, comparator)
	else:
		iterator = reverse(hits) if reverse else iter(hits)
		return iterator

# legacy results

def empty_search_results(query):
	result = component.getUtility(search_interfaces.ISearchResultsCreator)(query)
	return result

def empty_suggest_and_search_results(query):
	result = component.getUtility(
						search_interfaces.ISuggestAndSearchResultsCreator)(query)
	return result

def empty_suggest_results(query):
	result = component.getUtility(search_interfaces.ISuggestResultsCreator)(query)
	return result

def _preflight(a, b):
	if a is None and b is None:
		result = (None, True)
	elif a is None and b is not None:
		result = (b, True)
	elif a is not None and b is None:
		result = (a, True)
	else:
		result = (None, False)
	return result

def _merge(a, b):
	a += b
	for k, vb in b.__dict__.items():
		if not k.startswith('_'):
			va = a.__dict__.get(k, None)
			if vb != va:
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
