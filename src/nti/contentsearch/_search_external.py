# -*- coding: utf-8 -*-
"""
Search externalization

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import component
from zope import interface

from z3c.batching.batch import Batch

from pyramid.threadlocal import get_current_request

from nti.externalization import interfaces as ext_interfaces
from nti.externalization.singleton import SingletonDecorator
from nti.externalization.externalization import toExternalObject
from nti.externalization.datastructures import LocatedExternalDict

from nti.dataserver.links import Link

from ._search_hits import get_search_hit
from . import interfaces as search_interfaces
from ._search_highlights import HighlightInfo
from ._search_highlights import word_fragments_highlight

from .common import ( tags_, content_, title_, replacementContent_, redactionExplanation_)
from .common import (LAST_MODIFIED, SNIPPET, QUERY, HIT_COUNT, ITEMS, TOTAL_HIT_COUNT,
					 SUGGESTIONS, FRAGMENTS, PHRASE_SEARCH, TOTAL_FRAGMENTS, FIELD)

# highlight decorators

def _word_fragments_highlight(query=None, text=None):
	query = search_interfaces.ISearchQuery(query, None)
	if query and text:
		result = word_fragments_highlight(query, text, query.language)
	else:
		result = HighlightInfo()
	return result

# search hits

@component.adapter(search_interfaces.ISearchHit)
@interface.implementer(ext_interfaces.IExternalObjectDecorator)
class _SearchHitHighlightDecorator(object):

	__metaclass__ = SingletonDecorator
	
	def decorateExternalObject(self, original, external):
		query = original.query
		text = external.get(SNIPPET, None)
		hi = self.hilight_text(query, text)
		self.set_snippet(hi, external)

	def hilight_text(self, query, text):
		hi = _word_fragments_highlight(query, text)
		return hi
	
	def set_snippet(self, hi, external):
		external[SNIPPET] = hi.snippet
		if hi.fragments:
			external[FRAGMENTS] = toExternalObject(hi.fragments)
			external[TOTAL_FRAGMENTS] = hi.total_fragments

class _MultipleFieldSearchHitHighlightDecorator(_SearchHitHighlightDecorator):
	
	def decorate_on_source_fields(self, hit, external, sources):
		query = hit.query
		content_hi = None
		for field, text in sources:
			hi = _word_fragments_highlight(query, text)
			content_hi = hi if not content_hi else content_hi
			if hi.match_count > 0:
				self.set_snippet(hi, external)
				external[FIELD] = field
				return
			
		if content_hi:
			external[FIELD] = external[FIELD] = field
			self.set_snippet(content_hi, external)
			
@component.adapter(search_interfaces.IRedactionSearchHit)
@interface.implementer(ext_interfaces.IExternalObjectDecorator)
class _RedactionSearchHitHighlightDecorator(_MultipleFieldSearchHitHighlightDecorator):
	
	def decorateExternalObject(self, hit, external):
		sources = (	(content_,external.get(SNIPPET, None)), 
					(replacementContent_, hit.get_replacement_content()), 
					(redactionExplanation_, hit.get_redaction_explanation()))		
		self.decorate_on_source_fields(hit, external, sources)
	
@component.adapter(search_interfaces.IPostSearchHit)
@interface.implementer(ext_interfaces.IExternalObjectDecorator)
class _PostSearchHitHighlightDecorator(_MultipleFieldSearchHitHighlightDecorator):
	
	def decorateExternalObject(self, hit, external):
		sources = (	(content_,external.get(SNIPPET, None)),
					(title_, hit.get_title()), 
					(tags_, hit.get_tags()))	
		self.decorate_on_source_fields(hit, external, sources)
			
@interface.implementer(ext_interfaces.IExternalObject)
@component.adapter(search_interfaces.ISearchHit)
class _SearchHitExternalizer(object):
	
	__slots__ = ('hit',)
	
	def __init__( self, hit ):
		self.hit = hit

	def toExternalObject(self):
		return self.hit
	
# search results

@interface.implementer(ext_interfaces.IExternalObject)
class _BaseSearchResultsExternalizer(object):
	
	__slots__ = ('results',)
	
	def __init__( self, results ):
		self.results = results

	@property
	def query(self):
		return self.results.query
	
	def toExternalObject(self):
		eo = LocatedExternalDict()
		eo[QUERY] = self.query.term
		return eo

@component.adapter(search_interfaces.ISearchResults)
class _SearchResultsExternalizer(_BaseSearchResultsExternalizer):

	__slots__ = ('results', 'seen')
	
	def __init__( self, results ):
		super(_SearchResultsExternalizer, self).__init__(results)
		self.seen = set()

	@property
	def is_batching(self):
		return self.query.is_batching

	@property
	def batchSize(self):
		return self.query.batchSize

	@property
	def batchStart(self):
		return self.query.batchStart
	
	@property
	def hits(self):
		sortOn = self.query.sortOn
		if sortOn and not self.results.sorted:
			self.results.sort(sortOn)
	
		if self.is_batching:
			if self.batchStart < len(self.results):
				return Batch(self.results.hits, start=self.batchStart, size=self.batchSize)
			else:
				return ()
		else:
			return self.results.hits
		
	def toExternalObject(self):
		eo = super(_SearchResultsExternalizer, self).toExternalObject()
		eo[ITEMS] = items = []
		eo[PHRASE_SEARCH] = self.query.is_phrase_search
		
		# process hits
		count = 0
		last_modified = 0
		limit = self.query.limit

		for hit in self.hits:

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
		
		if self.query.is_batching:
			eo[TOTAL_HIT_COUNT] = len(self.results)
			
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

@component.adapter(search_interfaces.ISearchResults)
@interface.implementer(ext_interfaces.IExternalObjectDecorator)
class _SearchResultsLinkDecorator(object):

	__metaclass__ = SingletonDecorator
	
	def decorateExternalObject(self, original, external):
		query = original.query
		if query.is_batching:
			request = get_current_request()
			if request is None: return
			
			# Insert links to the next and previous batch
			result_list = Batch(original.hits, query.batchStart, query.batchSize)
			next_batch, prev_batch = result_list.next, result_list.previous
			for batch, rel in ((next_batch, 'batch-next'), (prev_batch, 'batch-prev')):
				if batch is not None and batch != result_list:
					batch_params = request.params.copy()
					batch_params['batchStart'] = batch.start
					link_next_href = request.current_route_path(_query=sorted(batch_params.items())) 
					link_next = Link( link_next_href, rel=rel )
					external.setdefault( 'Links', [] ).append( link_next )
