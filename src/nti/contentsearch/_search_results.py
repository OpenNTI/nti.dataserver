from __future__ import print_function, unicode_literals

import six

from zope import interface
from persistent.interfaces import IPersistent

from nti.contentsearch import interfaces as search_interfaces
from nti.contentsearch.common import (QUERY, HIT_COUNT, ITEMS, LAST_MODIFIED, SUGGESTIONS)

import logging
logger = logging.getLogger( __name__ )

class _BaseSearchResults(object):
	def __init__(self, query):
		assert search_interfaces.ISearchQuery.providedBy(query)
		self._query = query
	
	@property
	def limit(self):
		return self.query.limit
	
	@property
	def query(self):
		return self._query
	
	@property
	def hits(self):
		raise NotImplementedError()
	
	def __len__(self):
		return len(self.hits)
	
	def __getitem__(self, n):
		return self.hits[n]

	def __iter__(self):
		return iter(self.hits)

@interface.implementer( search_interfaces.ISearchResults )
class _SearchResults(_BaseSearchResults):
	def __init__(self, query):
		super(_SearchResults, self).__init__(query)
		self._hits = []

	@property
	def hits(self):
		return self._hits
	
	def add(self, items):
		items = tuple(items) if IPersistent.providedBy(items) else items
		for item in items or ():
			if IPersistent.providedBy(item):
				self.hits.append(item)
	
@interface.implementer( search_interfaces.ISuggestResults )
class _SuggestResults(_BaseSearchResults):
	def __init__(self, query):
		super(_SuggestResults, self).__init__(query)
		self._words = set()

	@property
	def hits(self):
		return self._words
	
	suggestions = hits
	
	def add_suggestions(self, items):
		items = tuple(items) if isinstance(items, six.string_types) else items
		for item in items or ():
			if isinstance(item, six.string_types):
				self.hits.add(unicode(item))
			
	add = add_suggestions

@interface.implementer( search_interfaces.ISuggestAndSearchResults )
class _SuggestAndSearchResults(_SearchResults, _SuggestResults):
	def __init__(self, query):
		super(_SearchResults, self).__init__(query)
		super(_SuggestResults, self).__init__(query)

	@property
	def hits(self):
		return self._hits
	
	@property
	def suggestions(self):
		return list(self._words)
			
	def add(self, items):
		_SearchResults.add(self, items)

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

def _empty_result(query, is_suggest=False):
	result = {}
	result[QUERY] = query
	result[HIT_COUNT] = 0
	result[ITEMS] = [] if is_suggest else {}
	result[LAST_MODIFIED] = 0
	return result

def empty_search_result(query):
	return _empty_result(query)

def empty_suggest_and_search_result(query):
	result = _empty_result(query)
	result[SUGGESTIONS] = []
	return result

def empty_suggest_result(word):
	return _empty_result(word, True)

def merge_search_results(a, b):

	if not a and not b:
		return None
	elif not a and b:
		return b
	elif a and not b:
		return a

	alm = a.get(LAST_MODIFIED, 0)
	blm = b.get(LAST_MODIFIED, 0)
	a[LAST_MODIFIED] = max(alm, blm)

	if not a.has_key(ITEMS):
		a[ITEMS] = {}
	
	a[ITEMS].update(b.get(ITEMS, {}))
	a[HIT_COUNT] = len(a[ITEMS])
	return a

def merge_suggest_and_search_results(a, b):
	result = merge_search_results(a, b)
	s_a = set(a.get(SUGGESTIONS, [])) if a else set([])
	s_b = set(b.get(SUGGESTIONS, [])) if b else set([])
	s_a.update(s_b)
	result[SUGGESTIONS] = list(s_a)
	return result

def merge_suggest_results(a, b):

	if not a and not b:
		return None
	elif not a and b:
		return b
	elif a and not b:
		return a

	alm = a.get(LAST_MODIFIED, 0)
	blm = b.get(LAST_MODIFIED, 0)
	a[LAST_MODIFIED] = max(alm, blm)

	if not a.has_key(ITEMS):
		a[ITEMS] = []
	
	a_set = set(a.get(ITEMS,[]))
	a_set.update(b.get(ITEMS,[]))
	a[ITEMS] = list(a_set)
	a[HIT_COUNT] = len(a[ITEMS])
	return a

