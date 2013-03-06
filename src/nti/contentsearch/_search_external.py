# -*- coding: utf-8 -*-
"""
Search externalization

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import collections

from zope import component
from zope import interface

from z3c.batching.batch import Batch

from nti.externalization import interfaces as ext_interfaces
from nti.externalization.singleton import SingletonDecorator
from nti.externalization.externalization import toExternalObject

from ._search_results import sort_hits
from ._search_hits import get_search_hit
from . import interfaces as search_interfaces
from ._search_highlights import HighlightInfo
from ._search_highlights import word_fragments_highlight

from .common import (LAST_MODIFIED, SNIPPET, QUERY, HIT_COUNT, ITEMS,
					 SUGGESTIONS, FRAGMENTS, PHRASE_SEARCH, TOTAL_FRAGMENTS)

# highlight decorators

def _word_fragments_highlight(query=None, text=None):
	query = search_interfaces.ISearchQuery(query, None)
	if query and text:
		result = word_fragments_highlight(query, text)
	else:
		result = HighlightInfo()
	return result

@component.adapter(search_interfaces.ISearchHit)
@interface.implementer(ext_interfaces.IExternalObjectDecorator)
class WordSnippetHighlightDecorator(object):

	__metaclass__ = SingletonDecorator
	
	def decorateExternalObject(self, original, external):
		query = getattr(original, 'query', None)
		if query:
			text = external.get(SNIPPET, None)
			hi = _word_fragments_highlight(query, text)
			external[SNIPPET] = hi.snippet
			if hi.fragments:
				external[FRAGMENTS] = toExternalObject(hi.fragments)
				external[TOTAL_FRAGMENTS] = hi.total_fragments


# search hits

@interface.implementer(ext_interfaces.IExternalObject)
@component.adapter(search_interfaces.ISearchHit)
class _SearchHitExternalizer(object):
	
	def __init__( self, hit ):
		self.hit = hit

	def toExternalObject(self):
		return self.hit
	
# search results

@interface.implementer(ext_interfaces.IExternalObject)
class _BaseSearchResultsExternalizer(object):
	
	def __init__( self, results ):
		self.results = results

	@property
	def query(self):
		return self.results.query

	@property
	def highlight_type(self):
		return getattr(self.results, 'highlight_type', None)

	def toExternalObject(self):
		eo = {QUERY: self.query.term}
		return eo

@component.adapter(search_interfaces.ISearchResults)
class _SearchResultsExternalizer(_BaseSearchResultsExternalizer):

	def __init__( self, results ):
		super(_SearchResultsExternalizer, self).__init__(results)
		self.seen = set()

	@property
	def is_batching(self):
		return self.results.is_batching

	@property
	def batchSize(self):
		return self.results.batchSize

	@property
	def batchStart(self):
		return self.results.batchStart
	
	def hit_iter(self):
		sortOn = self.query.sortOn
		iter_or_seq = sort_hits(self.results, sortOn=sortOn) if sortOn else self.results
		if self.is_batching:
			seq = iter_or_seq if isinstance(iter_or_seq, collections.Sequence) else list(iter_or_seq)
			batch = Batch(seq, start=self.batchStart, size=self.batchSize)
			return iter(batch)
		else:
			return iter(iter_or_seq) if isinstance(iter_or_seq, collections.Sequence) else iter_or_seq
		
	def toExternalObject(self):
		eo = super(_SearchResultsExternalizer, self).toExternalObject()
		eo[PHRASE_SEARCH] = self.query.is_phrase_search
		eo[ITEMS] = items = []

		# process hits
		count = 0
		last_modified = 0
		limit = self.query.limit

		# use iterator in case of any paging
		for hit in self.hit_iter():

			if hit is None or hit.obj is None:
				continue

			item = hit.obj
			score = hit.score
			query = hit.query

			hit = get_search_hit(item, score, query)
			if hit.oid in self.seen:
				continue

			self.seen.add(hit.oid)
			last_modified = max(last_modified, hit.last_modified)

			external = toExternalObject(hit)
			items.append(external)

			count += 1
			if count >= limit:
				break

		eo[HIT_COUNT] = len(items)
		eo[LAST_MODIFIED] = last_modified
		return eo

@component.adapter(search_interfaces.ISuggestResults)
class _SuggestResultsExternalizer(_BaseSearchResultsExternalizer):

	@property
	def suggestions(self):
		return self.results.suggestions

	def toExternalObject(self):
		eo = super(_SuggestResultsExternalizer, self).toExternalObject()
		items = [item for item in self.suggestions if item is not None]
		eo[ITEMS] = items
		eo[SUGGESTIONS] = items
		eo[HIT_COUNT] = len(items)
		eo[LAST_MODIFIED] = 0
		return eo

@component.adapter(search_interfaces.ISuggestAndSearchResults)
class _SuggestAndSearchResultsExternalizer(_SearchResultsExternalizer, _SuggestResultsExternalizer):

	def toExternalObject(self):
		eo = _SearchResultsExternalizer.toExternalObject(self)
		eo[SUGGESTIONS] = self.suggestions
		return eo
