from __future__ import print_function, unicode_literals

import UserDict

import zope.intid
from zope import component
from zope import interface

from nti.dataserver import interfaces as nti_interfaces
from nti.chatserver import interfaces as chat_interfaces
from nti.externalization import interfaces as ext_interfaces
from nti.externalization.externalization import toExternalObject

from nti.contentsearch import interfaces as search_interfaces

from nti.contentsearch.common import epoch_time
from nti.contentsearch.common import clean_query
from nti.contentsearch._search_highlights import (word_content_highlight, ngram_content_highlight)
from nti.contentsearch._search_highlights import (WORD_HIGHLIGHT, NGRAM_HIGHLIGHT, WHOOSH_HIGHLIGHT)

from nti.contentsearch.common import (	NTIID, CREATOR, LAST_MODIFIED, CONTAINER_ID, CLASS, TYPE,
										SNIPPET, HIT, ID, TARGET_OID, CONTENT, INTID, QUERY,
										HIT_COUNT, ITEMS, SUGGESTIONS)

from nti.contentsearch.common import ( last_modified_, content_, title_, ntiid_)

import logging
logger = logging.getLogger( __name__ )

# hilight decorators

def _word_content_highlight(query=None, text=None, default=None):
	query = clean_query(query) if query else u''
	content = word_content_highlight(query, text) if query and text else u''
	return unicode(content) if content else default

def _ngram_content_highlight(query=None, text=None, default=None):
	query = clean_query(query) if query else u''
	content = ngram_content_highlight(query, text) if query and text else u''
	return unicode(content) if content else default

@interface.implementer(ext_interfaces.IExternalObjectDecorator)
class _BaseHighlightDecorator(object):
	
	@classmethod
	def get_query_term(cls, original):
		query = getattr(original, 'query', None)
		if query and search_interfaces.ISearchQuery.providedBy(query):
			query = query.term
		return query
	
	@classmethod
	def decorateExternalObject(cls, original, external):
		pass
	
@component.adapter(search_interfaces.INoSnippetHighlight)
class NoSnippetHighlightDecorator(_BaseHighlightDecorator):
	pass
	
def NoSnippetHighlightDecoratorFactory(*args):
	return NoSnippetHighlightDecorator()
				
class _BaseNgramSnippetHighlightDecorator(_BaseHighlightDecorator):
	
	def decorateExternalObject(self, original, external):
		query = self.get_query_term(original)
		if query:
			text = external.get(SNIPPET, None)
			text = _ngram_content_highlight(query, text.lower(), text)
			external[SNIPPET] = text
			
@component.adapter(search_interfaces.INgramSnippetHighlight)
class NgramSnippetHighlightDecorator(_BaseNgramSnippetHighlightDecorator):
	pass
	
def NgramSnippetHighlightDecoratorFactory(*args):
	return NgramSnippetHighlightDecorator()

@interface.implementer(ext_interfaces.IExternalObjectDecorator)
class _BaseWordSnippetHighlightDecorator(_BaseHighlightDecorator):

	def decorateExternalObject(self, original, external):
		query = self.get_query_term(original)
		if query:
			text = external.get(SNIPPET, None)
			text = _word_content_highlight(query, text, text)
			external[SNIPPET] = text
			
@component.adapter(search_interfaces.IWordSnippetHighlight)
class WordSnippetHighlightDecorator(_BaseWordSnippetHighlightDecorator):
	pass
	
def WordSnippetHighlightDecoratorFactory(*args):
	return WordSnippetHighlightDecorator()

@component.adapter(search_interfaces.IWhooshSnippetHighlight)
class WhooshHighlightDecorator(_BaseWordSnippetHighlightDecorator):

	def decorateExternalObject(self, original, external):
		#whoosh_highlight = getattr(original, 'whoosh_highlight', None)
		#if whoosh_highlight:
		#	external[SNIPPET] = whoosh_highlight
		#else:
		super(WhooshHighlightDecorator, self).decorateExternalObject(original, external)

def WhooshHighlightDecoratorFactory(*args):
	return WhooshHighlightDecorator()

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
		eo[HIT_COUNT] = len(self.results)
		return eo
	
@component.adapter(search_interfaces.ISearchResults)
class _SearchResultsExternalizer(_BaseSearchResultsExternalizer):
	
	@property
	def hits(self):
		return self.results.hits
	items = hits
	
	def toExternalObject(self):
		eo = super(_SearchResultsExternalizer, self).toExternalObject()
		eo[ITEMS] = items = []
		
		# process hits
		query = self.query
		last_modified = 0
		highlight_type = self.highlight_type
		for item in self.items:
			# adapt to a search hit 
			hit = get_search_hit(item, query, highlight_type)
			last_modified = max(last_modified, hit.last_modified)
			# run any decorator
			external = toExternalObject(hit)
			items.append(external)
			
		eo[LAST_MODIFIED] = last_modified
		return eo

@component.adapter(search_interfaces.ISuggestResults)
class _SuggestResultsExternalizer(_BaseSearchResultsExternalizer):
	
	@property
	def suggestions(self):
		return sorted(self.results.suggestions, key=lambda x: len(x), reverse=True)
	
	def toExternalObject(self):
		eo = super(_SuggestResultsExternalizer, self).toExternalObject()
		eo[ITEMS] = self.suggestions
		eo[SUGGESTIONS] = eo[ITEMS]
		eo[LAST_MODIFIED] = 0 
		return eo
	
@component.adapter(search_interfaces.ISuggestAndSearchResults)
class _SuggestAndSearchResultsExternalizer(_SearchResultsExternalizer, _SuggestResultsExternalizer):
	
	def toExternalObject(self):
		eo = _SearchResultsExternalizer.toExternalObject(self)
		eo[SUGGESTIONS] = self.get_suggestions()
		return eo
	
# search hits

hit_search_external_fields  = (	CLASS, CREATOR, TARGET_OID, TYPE, LAST_MODIFIED, NTIID, \
								CONTAINER_ID, SNIPPET, ID, INTID)

def get_uid(obj):
	_ds_intid = component.getUtility( zope.intid.IIntIds )
	uid = _ds_intid.getId(obj)
	return uid

@interface.implementer(search_interfaces.ISearchHit)
class _BaseSearchHit(object, UserDict.DictMixin):
	def __init__( self ):
		self._data = {}
		self._query = None
		
	def toExternalObject(self):
		return self._data
	
	def keys(self):
		return self._data.keys()
	
	def __getitem__(self, key):
		return self._data[key]
	
	def __setitem__(self, key, val):
		self._data[key] = val
		
	def __delitem__(self, key):
		self._data.pop(key)
		
	def __repr__(self):
		return "<%s %r>" % (self.__class__.__name__, self._data)
	
class _SearchHit(_BaseSearchHit):
	def __init__( self, original ):
		super(_SearchHit, self).__init__()
		adapted = component.queryAdapter(original, search_interfaces.IContentResolver)
		self._data[CLASS] = HIT
		self._data[TYPE] = original.__class__.__name__
		self._data[CREATOR] = adapted.get_creator() if adapted else u''
		self._data[NTIID] = adapted.get_ntiid() if adapted else u''
		self._data[SNIPPET] = adapted.get_content() if adapted else u''
		self._data[TARGET_OID] = adapted.get_external_oid() if adapted else u''
		self._data[CONTAINER_ID] = adapted.get_containerId() if adapted else u''
		self._data[LAST_MODIFIED] = adapted.get_last_modified() if adapted else 0
		
	def get_query(self):
		return self._query if search_interfaces.ISearchQuery.providedBy(self._query) else self._query
	
	def set_query(self, query):
		self._query = query
		
	query = property(get_query, set_query)
	
	@property
	def last_modified(self):
		return self._data.get(LAST_MODIFIED, 0)
		
@component.adapter(nti_interfaces.IHighlight)
class _HighlightSearchHit(_SearchHit):
	pass
	
@component.adapter(nti_interfaces.IRedaction)
class _RedactionSearchHit(_SearchHit):
	pass
		
@component.adapter(nti_interfaces.INote)
class _NoteSearchHit(_SearchHit):
	pass
	
@component.adapter(chat_interfaces.IMessageInfo)
class _MessageInfoSearchHit(_SearchHit):
	def __init__( self, original ):
		super(_MessageInfoSearchHit, self).__init__(original)
		adapted = component.queryAdapter(original, search_interfaces.IContentResolver)
		self._data[ID] = adapted.get_id() if adapted else u''
		
@component.adapter(search_interfaces.IWhooshBookContent)
class _WhooshBookSearchHit(_BaseSearchHit):
	
	def __init__( self, hit ):
		super(_WhooshBookSearchHit, self).__init__()
		self._data[CLASS] = HIT	
		self._data[TYPE] = CONTENT
		self._data[NTIID] = hit[ntiid_]
		self._data[SNIPPET] = hit[content_]
		self._data[CONTAINER_ID] = hit[ntiid_]
		self._data[title_.capitalize()] = hit[title_]
		self._data[LAST_MODIFIED] = epoch_time(hit[last_modified_])
		
		# set whoosh highlight
		self.whoosh_highlight = None
		search_field = getattr(hit, 'search_field', None)
		if search_field:
			try:
				self.whoosh_highlight = hit.highlights(search_field)
			except:
				pass
		
def _provide_highlight_snippet(hit, query=None, highlight_type=WORD_HIGHLIGHT):
	if hit is not None:
		hit.query = query
		if highlight_type == NGRAM_HIGHLIGHT:
			interface.alsoProvides( hit, search_interfaces.INgramSnippetHighlight )
		elif highlight_type == WORD_HIGHLIGHT:
			interface.alsoProvides( hit, search_interfaces.IWordSnippetHighlight )
		elif highlight_type == WHOOSH_HIGHLIGHT:
			interface.alsoProvides( hit, search_interfaces.IWhooshSnippetHighlight )
		else:
			interface.alsoProvides( hit, search_interfaces.INoSnippetHighlight )
	return hit

def get_search_hit(obj, query=None, highlight_type=WORD_HIGHLIGHT):
	hit = component.queryAdapter( obj, ext_interfaces.IExternalObject, default=None, name='search-hit')
	hit = hit or _SearchHit(obj)
	hit = _provide_highlight_snippet(hit, query, highlight_type)
	return hit
