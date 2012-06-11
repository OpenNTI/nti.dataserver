import UserDict

from zope import component
from zope import interface

from nti.dataserver import interfaces as nti_interfaces
from nti.chatserver import interfaces as chat_interfaces
from nti.externalization import interfaces as ext_interfaces
from nti.externalization.externalization import toExternalObject

from nti.contentsearch import interfaces as search_interfaces

from nti.contentsearch.common import get_attr
from nti.contentsearch.common import get_content
from nti.contentsearch.common import clean_query
from nti.contentsearch.common import get_multipart_content
from nti.contentsearch.common import word_content_highlight
from nti.contentsearch.common import ngram_content_highlight

from nti.contentsearch.common import (	WORD_HIGHLIGHT, NGRAM_HIGHLIGHT)

from nti.contentsearch.common import (	NTIID, CREATOR, LAST_MODIFIED, CONTAINER_ID, CLASS, TYPE,
										SNIPPET, HIT, ID, BODY, TARGET_OID, OID)

from nti.contentsearch.common import (	body_, highlightedText_, last_modified_, content_)


import logging
logger = logging.getLogger( __name__ )

# -----------------------------------

def _word_content_highlight(query=None, text=None, default=None):
	query = clean_query(query) if query else u''
	content = word_content_highlight(query, text) if query and text else u''
	return unicode(content) if content else default

def _ngram_content_highlight(query=None, text=None, default=None):
	query = clean_query(query) if query else u''
	content = ngram_content_highlight(query, text) if query and text else u''
	return unicode(content) if content else default

def _highlight_content(query=None, text=None, highlight_type=True):
	content = None
	if query and text:
		if highlight_type == WORD_HIGHLIGHT:
			content = _word_content_highlight(query, text)
		elif highlight_type == NGRAM_HIGHLIGHT:
			content = _ngram_content_highlight(query, text)
		else:
			content = text
	return unicode(content) if content else text

def NoSnippetHighlightDecoratorFactory(*args):
	return NoSnippetHighlightDecorator()

class NoSnippetHighlightDecorator(object):
	interface.implements(ext_interfaces.IExternalObjectDecorator)
	component.adapts(search_interfaces.INoSnippetHighlight)

	def decorateExternalObject(self, original, external):
		pass
			
def WordSnippetHighlightDecoratorFactory(*args):
	return WordSnippetHighlightDecorator()
	
class WordSnippetHighlightDecorator(object):
	interface.implements(ext_interfaces.IExternalObjectDecorator)
	component.adapts(search_interfaces.IWordSnippetHighlight)

	def decorateExternalObject(self, original, external):
		query = getattr(original, 'query', None)
		if query:
			text = external.get(SNIPPET, None)
			text = _word_content_highlight(query, text, text)
			external[SNIPPET] = text
		
def NgramSnippetHighlightDecoratorFactory(*args):
	return NgramSnippetHighlightDecorator()

class NgramSnippetHighlightDecorator(object):
	interface.implements(ext_interfaces.IExternalObjectDecorator)
	component.adapts(search_interfaces.INgramSnippetHighlight)

	def decorateExternalObject(self, original, external):
		query = getattr(original, 'query', None)
		if query:
			text = external.get(SNIPPET, None)
			text = _ngram_content_highlight(query, text, text)
			external[SNIPPET] = text
			
# -----------------------------------

search_external_fields  = (CLASS, CREATOR, TARGET_OID, TYPE, LAST_MODIFIED, NTIID, CONTAINER_ID, SNIPPET, ID)
	
class _SearchHit(object, UserDict.DictMixin):
	interface.implements( search_interfaces.ISearchHit )
	
	__external_fields  = search_external_fields
	
	def __init__( self, entity ):
		if type(entity) == dict:
			self._data = dict(entity)
		else:
			self._data = toExternalObject(entity) if entity else {}
		self._supplement(self._data)
		self._reduce(self._data)
		self.query = None
	
	def _supplement(self, data):
		if CLASS in data:
			data[TYPE] = data[CLASS]
		if OID in data:
			data[TARGET_OID] = data[OID]
		if last_modified_ in data:
			data[LAST_MODIFIED] = data[last_modified_]
		if content_ in data:
			data[SNIPPET] = data[content_]
			
		data[CLASS] = HIT
		data[NTIID] = data.get(NTIID, None) or data.get(TARGET_OID, None)
		
	def _reduce(self, data):
		for key in list(data.keys()):
			if not key in search_external_fields:
				data.pop(key)
	
	def keys(self):
		return self._data.keys()
		
	def __getitem__(self, key):
		return self._data[key]
	
	def __setitem__(self, key, val):
		self._data[key] = val
		
	def __delitem__(self, key):
		self._data.pop(key)
	
	def toExternalObject(self):
		return dict(self._data)
		
class _HighlightSearchHit(_SearchHit):
	component.adapts( nti_interfaces.IHighlight )
	
	def _supplement(self, data):
		super(_HighlightSearchHit, self)._supplement(data)
		text = get_content(get_attr(data, [highlightedText_]))
		data[SNIPPET] = text
	
class _NoteSearchHit(_SearchHit):
	component.adapts( nti_interfaces.INote )

	def _supplement(self, data):
		super(_NoteSearchHit, self)._supplement(data)
		text = get_multipart_content(get_attr(data, [body_]))
		data[SNIPPET] = text
	
class _MessageInfoSearchHit(_SearchHit):
	component.adapts( chat_interfaces.IMessageInfo )

	def _supplement(self, data):
		super(_MessageInfoSearchHit, self)._supplement(data)
		text = get_multipart_content(get_attr(data, [BODY]))
		data[SNIPPET] = text
		
def _provide_highlight_snippet(hit, query=None, highlight_type=WORD_HIGHLIGHT):
	if hit is not None:
		hit.query = query
		if highlight_type == NGRAM_HIGHLIGHT:
			interface.alsoProvides( hit, search_interfaces.INgramSnippetHighlight )
		elif highlight_type == WORD_HIGHLIGHT:
			interface.alsoProvides( hit, search_interfaces.IWordSnippetHighlight )
		else:
			interface.alsoProvides( hit, search_interfaces.INoSnippetHighlight )
	return hit

def get_search_hit(obj, query=None, highlight_type=WORD_HIGHLIGHT, *args, **kwargs):
	hit = component.queryAdapter( obj, ext_interfaces.IExternalObject, default=_SearchHit(obj), name='search-hit')
	hit = _provide_highlight_snippet(hit, query, highlight_type)
	return hit
