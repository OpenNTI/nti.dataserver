from __future__ import print_function, unicode_literals

import six
from collections import Iterable

from z3c.batching.batch import Batch

from zope import interface
from zope import component
from zope.location import ILocation
from zope.mimetype import interfaces as zmime_interfaces

from nti.mimetype.mimetype import nti_mimetype_with_class

from nti.contentsearch import interfaces as search_interfaces

import logging
logger = logging.getLogger( __name__ )

@interface.implementer( ILocation )
class _BaseSearchResults(object):
	
	__name__ = None
	__parent__ = None
	
	def __init__(self, query):
		assert search_interfaces.ISearchQuery.providedBy(query)
		self._query = query
	
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

	@property
	def hits(self):
		return self._hits
	
	def add(self, items):
		items = [items] if not isinstance(items, Iterable)  else items
		for item in items or ():
			if item is not None:
				self._hits.append(item)
				
	def __iadd__(self, other):
		if 	search_interfaces.ISearchResults.providedBy(other) or \
			search_interfaces.ISuggestAndSearchResults.providedBy(other):
			self._hits.extend(other.hits)
		return self
	
@interface.implementer( search_interfaces.ISuggestResults )
class _SuggestResults(_BaseSearchResults):
	
	__metaclass__ = _MetaSearchResults
	
	def __init__(self, query):
		super(_SuggestResults, self).__init__(query)
		self._words = set()

	@property
	def hits(self):
		return self._words
	
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

	@property
	def hits(self):
		return self._hits
	
	@property
	def suggestions(self):
		return self._words
			
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

