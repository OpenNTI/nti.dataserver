# -*- coding: utf-8 -*-
"""
Search results

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import six
from collections import Iterable, namedtuple, defaultdict

from zope import interface
from zope import component
from zope.container import contained as zcontained
from zope.mimetype import interfaces as zmime_interfaces

from z3c.batching.batch import Batch

from nti.mimetype.mimetype import nti_mimetype_with_class

from ._search_utils import isorted
from . import interfaces as search_interfaces

class _BaseSearchResults(zcontained.Contained):

	def __init__(self, query):
		assert search_interfaces.ISearchQuery.providedBy(query)
		self._query = query

	def __str__( self ):
		return self.__repr__()

	def __repr__( self ):
		return '%s(hits=%s)' % (self.__class__.__name__, self.total)

	@property
	def query(self):
		return self._query

	@property
	def hits(self):
		raise NotImplementedError()

	@property
	def total(self):
		return len(self.hits)

	def __len__(self):
		return len(self.hits)

	def __getitem__(self, n):
		return self.hits[n]

	def __iter__(self):
		return iter(self.hits)

class _PageableSearchResults(_BaseSearchResults):

	@property
	def is_batching(self):
		return self.batchStart is not None and self.batchSize

	@property
	def batchSize(self):
		return self.query.batchSize

	def batchStart(self):
		return self.query.batchStart

	def _batch(self):
		return Batch(self.hits, start=self.batchStart, size=self.batchSize)

	def __getitem__(self, n):
		if self.is_batching:
			result = self._batch()[n]
		else:
			result = super(_PageableSearchResults, self).__getitem__(n)
		return result

	def __iter__(self):
		if self.is_batching:
			return iter(self._batch())
		else:
			return super(_PageableSearchResults, self).__iter__()

_IndexHit = namedtuple('_IndexHit', 'obj score query')

@interface.implementer(search_interfaces.IIndexHitMetaDataTracker)
class _IndexHitMetaDataTracker(object):

	def __init__(self):
		self._last_modified = 0
		self._container_count = defaultdict(int)

	def track(self, ihit):
		# unique container count
		rsr = search_interfaces.IContainerIDResolver(ihit.obj)
		containerId = rsr.get_containerId() or u'++unknown-container'
		self._container_count[containerId] = self._container_count[containerId] + 1

		# last modified
		rsr = search_interfaces.ILastModifiedResolver(ihit.obj)
		self._last_modified  = max(self._last_modified, rsr.get_last_modified() or 0)

	def __iadd__(self, other):
		# unique container count
		for k,v in other._container_count.items():
			self._container_count[k] = self._container_count[k] + v
		# last modified
		self._last_modified = max(self._last_modified, other._last_modified)
		return self

class _MetaSearchResults(type):

	def __new__(cls, name, bases, dct):
		t = type.__new__(cls, name, bases, dct)
		t.mime_type = nti_mimetype_with_class( name[1:] )
		return t

@interface.implementer( search_interfaces.ISearchResults,
						zmime_interfaces.IContentTypeAware )
class _SearchResults(_PageableSearchResults):

	__metaclass__ = _MetaSearchResults

	def __init__(self, query):
		super(_SearchResults, self).__init__(query)
		self._hits = []
		self._ihitmeta = _IndexHitMetaDataTracker()

	def get_hits(self):
		return self._hits
	
	def get_hit_meta_data(self):
		return self._ihitmeta

	hits = property(get_hits)
	hit_meta_data = property(get_hit_meta_data)

	def _add(self, item):
		ihit = None
		if search_interfaces.IIndexHit.providedBy(item):
			if item.obj is not None:
				item.query = self.query
				ihit = item
		elif isinstance(item, tuple):
			if item[0] is not None:
				ihit = _IndexHit(item[0], item[1], self.query)
		elif item is not None:
			ihit = _IndexHit(item, 1.0, self.query)

		if ihit is not None:
			self._hits.append(ihit)
			self._ihitmeta.track(ihit)

	def add(self, hits):
		if search_interfaces.IIndexHit.providedBy(hits) or isinstance(hits, tuple):
			items = [hits]
		else:
			items = [hits] if not isinstance(hits, Iterable) else hits

		for item in items or ():
			self._add(item)

	def sort(self):
		sortOn = self.query.sortOn
		comparator = component.queryUtility(search_interfaces.ISearchHitComparator, name=sortOn) if sortOn else None
		if comparator is not None:
			reverse = not self.query.is_descending_sort_order
			self._hits.sort(comparator.compare, reverse=reverse)

	def __iadd__(self, other):
		if 	search_interfaces.ISearchResults.providedBy(other) or \
			search_interfaces.ISuggestAndSearchResults.providedBy(other):

			self._ihitmeta += other._ihitmeta
			self._hits.extend(other.hits)

		return self

@interface.implementer( search_interfaces.ISuggestResults )
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
		items = [items] if isinstance(items, six.string_types) or not isinstance(items, Iterable) else items
		for item in items or ():
			if isinstance(item, six.string_types):
				self._words.add(unicode(item))

	add = add_suggestions

	def __iadd__(self, other):
		if 	search_interfaces.ISuggestResults.providedBy(other) or \
			search_interfaces.ISuggestAndSearchResults.providedBy(other):
			self._words.update(other.suggestions)
		return self

@interface.implementer( search_interfaces.ISuggestAndSearchResults )
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

	def add(self, items):
		_SearchResults.add(self, items)

	def __iadd__(self, other):
		_SearchResults.__iadd__(self, other)
		_SuggestResults.__iadd__(self, other)
		return self

@interface.implementer( search_interfaces.ISearchResultsCreator )
class _SearchResultCreator(object):
	def __call__(self, query):
		return _SearchResults(query)

@interface.implementer( search_interfaces.ISuggestResultsCreator )
class _SuggestResultsCreator(object):
	def __call__(self, query):
		return _SuggestResults(query)

@interface.implementer( search_interfaces.ISuggestAndSearchResultsCreator)
class _SuggestAndSearchResultsCreator(object):
	def __call__(self, query):
		return _SuggestAndSearchResults(query)

# sort

def sort_hits(hits, reverse=False, sortOn=None):
	comparator = component.queryUtility(search_interfaces.ISearchHitComparator, name=sortOn) if sortOn else None
	if comparator is not None:
		if reverse:
			comparator = lambda x,y: comparator(y,x)
		return isorted(hits, comparator)
	else:
		iterator = reverse(hits) if reverse else iter(hits)
		return iterator

# legacy results

def empty_search_results(query):
	result = component.getUtility(search_interfaces.ISearchResultsCreator)(query)
	return result

def empty_suggest_and_search_results(query):
	result = component.getUtility(search_interfaces.ISuggestAndSearchResultsCreator)(query)
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
