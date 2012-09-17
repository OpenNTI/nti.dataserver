from __future__ import print_function, unicode_literals

import UserDict

import zope.intid
from zope import component
from zope import interface
from persistent.interfaces import IPersistent

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
										SNIPPET, HIT, ID, TARGET_OID, OID, CONTENT, INTID)

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

def NoSnippetHighlightDecoratorFactory(*args):
	return NoSnippetHighlightDecorator()

@interface.implementer(ext_interfaces.IExternalObjectDecorator)
@component.adapter(search_interfaces.INoSnippetHighlight)
class NoSnippetHighlightDecorator(object):

	def decorateExternalObject(self, original, external):
		pass
					
def NgramSnippetHighlightDecoratorFactory(*args):
	return NgramSnippetHighlightDecorator()

@interface.implementer(ext_interfaces.IExternalObjectDecorator)
class _BaseNgramSnippetHighlightDecorator(object):
	
	def decorateExternalObject(self, original, external):
		query = getattr(original, 'query', None)
		if query:
			text = external.get(SNIPPET, None)
			text = _ngram_content_highlight(query, text.lower(), text)
			external[SNIPPET] = text
			
@component.adapter(search_interfaces.INgramSnippetHighlight)
class NgramSnippetHighlightDecorator(_BaseNgramSnippetHighlightDecorator):
	pass
		
def WhooshHighlightDecoratorFactory(*args):
	return WhooshHighlightDecorator()
	
def WordSnippetHighlightDecoratorFactory(*args):
	return WordSnippetHighlightDecorator()
	
@interface.implementer(ext_interfaces.IExternalObjectDecorator)
class _BaseWordSnippetHighlightDecorator(object):

	def decorateExternalObject(self, original, external):
		query = getattr(original, 'query', None)
		if query:
			text = external.get(SNIPPET, None)
			text = _word_content_highlight(query, text, text)
			external[SNIPPET] = text
			
@component.adapter(search_interfaces.IWordSnippetHighlight)
class WordSnippetHighlightDecorator(_BaseWordSnippetHighlightDecorator):
	pass
	
@component.adapter(search_interfaces.IWhooshSnippetHighlight)
class WhooshHighlightDecorator(_BaseWordSnippetHighlightDecorator):

	def decorateExternalObject(self, original, external):
		#whoosh_highlight = getattr(original, 'whoosh_highlight', None)
		#if whoosh_highlight:
		#	external[SNIPPET] = whoosh_highlight
		#else:
		super(WhooshHighlightDecorator, self).decorateExternalObject(original, external)

# search results


# search hits

search_external_fields  = (	CLASS, CREATOR, TARGET_OID, TYPE, LAST_MODIFIED, NTIID, \
							CONTAINER_ID, SNIPPET, ID, INTID)
	
default_search_hit_mappings =  ((CLASS, TYPE), (OID, TARGET_OID), \
								(last_modified_, LAST_MODIFIED), (content_, SNIPPET) )
def get_content(obj):
	adapted = component.queryAdapter(obj, search_interfaces.IContentResolver)
	result = adapted.get_content() if adapted else u''
	return result

def get_uid(obj):
	_ds_intid = component.getUtility( zope.intid.IIntIds )
	uid = _ds_intid.getId(obj)
	return uid

@interface.implementer(search_interfaces.ISearchHit)
class _SearchHit(object, UserDict.DictMixin):
	
	def __init__( self, original ):
		if IPersistent.providedBy(original):
			self._data = toExternalObject(original)
		else:
			self._data = dict(original) if original else {}
			
		self._supplement(original, self._data)
		self._reduce(self._data)
		self.query = None
	
	def _supplement(self, original, external, intid=None):
		for k, r in default_search_hit_mappings:
			if k in external:
				external[r] = external[k]
				
		if SNIPPET not in external:
			external[SNIPPET] = get_content(original)
		
		if intid is not None:
			external[INTID] = intid
			
		external[CLASS] = HIT
		external[NTIID] = external.get(NTIID, None) or external.get(TARGET_OID, None)
		
	def _reduce(self, data):
		for key in list(data.keys()):
			if not key in search_external_fields:
				data.pop(key)
	
	def keys(self):
		return self._data.keys()
			
	def toExternalObject(self):
		return dict(self._data)
	
	def __getitem__(self, key):
		return self._data[key]
	
	def __setitem__(self, key, val):
		self._data[key] = val
		
	def __delitem__(self, key):
		self._data.pop(key)
		
	def __repr__(self):
		return "<%s %r>" % (self.__class__.__name__, self._data)
		
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
	pass
		
@component.adapter(search_interfaces.IWhooshBookContent)
class _WhooshBookSearchHit(_SearchHit):
	
	def __init__( self, hit ):
		self._data = {}	
		self.query = None
		self.whoosh_highlight = None
		self._supplement(hit, self._data)
	
	def _supplement(self, hit, external, *args, **kwargs):
		external[CLASS] = HIT	
		external[TYPE] = CONTENT
		external[NTIID] = hit[ntiid_]
		external[SNIPPET] = hit[content_]
		external[CONTAINER_ID] = hit[ntiid_]
		external[title_.capitalize()] = hit[title_]
		external[LAST_MODIFIED] = epoch_time(hit[last_modified_])
		self.set_whoosh_highlight(hit, external)

	def set_whoosh_highlight(self, hit, external):
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

def get_search_hit(obj, query=None, highlight_type=WORD_HIGHLIGHT, *args, **kwargs):
	hit = component.queryAdapter( obj, ext_interfaces.IExternalObject, default=None, name='search-hit')
	hit = hit or _SearchHit(obj)
	hit = _provide_highlight_snippet(hit, query, highlight_type)
	return hit
