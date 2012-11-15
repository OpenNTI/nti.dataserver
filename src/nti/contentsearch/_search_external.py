from __future__ import print_function, unicode_literals

from zope import component
from zope import interface

from nti.externalization import interfaces as ext_interfaces
from nti.externalization.externalization import toExternalObject

from nti.contentsearch import interfaces as search_interfaces

from nti.contentsearch._search_hits import get_search_hit
from nti.contentsearch._search_highlights import word_fragments_highlight

from nti.contentsearch.common import (	LAST_MODIFIED, SNIPPET, QUERY, HIT_COUNT, ITEMS,
										SUGGESTIONS, FRAGMENTS, PHRASE_SEARCH)

import logging
logger = logging.getLogger( __name__ )

# highlight decorators

def _word_fragments_highlight(query=None, text=None):
	query = search_interfaces.ISearchQuery(query, None)
	if query and text:
		snippet, fragments = word_fragments_highlight(query, text)
	else:
		snippet, fragments = (text or u'', ())
	return unicode(snippet), fragments

@interface.implementer(ext_interfaces.IExternalObjectDecorator)
class _BaseHighlightDecorator(object):
	
	@classmethod
	def decorateExternalObject(cls, original, external):
		pass
	
@component.adapter(search_interfaces.INoSnippetHighlight)
class NoSnippetHighlightDecorator(_BaseHighlightDecorator):
	pass
	
def NoSnippetHighlightDecoratorFactory(*args):
	return NoSnippetHighlightDecorator()
				
@interface.implementer(ext_interfaces.IExternalObjectDecorator)
class _BaseWordSnippetHighlightDecorator(_BaseHighlightDecorator):

	def decorateExternalObject(self, original, external):
		query = getattr(original, 'query', None)
		if query:
			text = external.get(SNIPPET, None)
			text, fragments = _word_fragments_highlight(query, text)
			external[SNIPPET] = text
			if fragments:
				external[FRAGMENTS] = toExternalObject(fragments)
			
@component.adapter(search_interfaces.IWordSnippetHighlight)
class WordSnippetHighlightDecorator(_BaseWordSnippetHighlightDecorator):
	pass
	
def WordSnippetHighlightDecoratorFactory(*args):
	return WordSnippetHighlightDecorator()

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
	
	def toExternalObject(self):
		eo = super(_SearchResultsExternalizer, self).toExternalObject()
		eo[PHRASE_SEARCH] = self.query.is_phrase_search
		eo[ITEMS] = items = []
		
		# process hits
		count = 0
		last_modified = 0
		limit = self.query.limit
		highlight_type = self.highlight_type
			
		# sort 
		self.results.sort()
		
		# use iterator in case of any paging
		for hit in self.results:
		
			if hit is None or hit.obj is None:
				continue
			
			item = hit.obj
			score = hit.score
			query = hit.query
				
			# adapt to a search hit 
			hit = get_search_hit(item, score, query, highlight_type)
			if hit.oid in self.seen:
				continue
			
			self.seen.add(hit.oid)
			last_modified = max(last_modified, hit.last_modified)
			# run any decorator
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
	
