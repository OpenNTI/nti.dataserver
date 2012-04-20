from zope import component
from zope import interface

from nti.dataserver import interfaces as nti_interfaces
from nti.chatserver import interfaces as chat_interfaces

from nti.contentsearch.common import get_attr
from nti.contentsearch.common import get_ntiid
from nti.contentsearch.common import get_content
from nti.contentsearch.common import get_creator
from nti.contentsearch.common import get_type_name
from nti.contentsearch.common import get_external_oid
from nti.contentsearch.common import get_last_modified
from nti.contentsearch.common import get_multipart_content
from nti.contentsearch.common import word_content_highlight
from nti.contentsearch.common import ngram_content_highlight

from nti.contentsearch.common import (	WORD_HIGHLIGHT, NGRAM_HIGHLIGHT)

from nti.contentsearch.common import (	NTIID, CREATOR, LAST_MODIFIED, CONTAINER_ID, CLASS, TYPE,
										SNIPPET, HIT, ID, BODY, TARGET_OID, MESSAGE_INFO)

from nti.contentsearch.common import (	container_id_fields,  body_, startHighlightedFullText_)


import logging
logger = logging.getLogger( __name__ )

# -----------------------------------

def _word_content_highlight(query=None, text=None, *args, **kwargs):
	content = word_content_highlight(query, text, *args, **kwargs) if query and text else u''
	return unicode(content) if content else text

def _ngram_content_highlight(query=None, text=None, *args, **kwargs):
	content = ngram_content_highlight(query, text, *args, **kwargs) if query and text else u''
	return unicode(content) if content else text

def _highlight_content(query=None, text=None, highlight_type=True, *args, **kwargs):
	content = None
	if query and text:
		if highlight_type == WORD_HIGHLIGHT:
			content = _word_content_highlight(query, text, *args, **kwargs)
		elif highlight_type == NGRAM_HIGHLIGHT:
			content = _ngram_content_highlight(query, text, *args, **kwargs)
		else:
			content = text
	return unicode(content) if content else text


class _MixinExternalObject(object):
	def __init__( self, entity ):
		self.entity = entity
	
	def toExternalObject(self):
		obj = self.entity
		result = {}
		result[CLASS] = HIT
		result[CREATOR] = get_creator(obj)
		result[TARGET_OID] = get_external_oid(obj)
		result[TYPE] = get_type_name(obj).capitalize()
		result[LAST_MODIFIED] = get_last_modified(obj)
		result[NTIID] = get_ntiid(obj) or result[TARGET_OID]
		result[CONTAINER_ID] = get_attr(obj, container_id_fields)
		#result[COLLECTION_ID] = get_collection(result[CONTAINER_ID])
		return result
		
class _HighlightExternalObject(_MixinExternalObject):
	component.adapts( nti_interfaces.IHighlight )
	interface.implements( nti_interfaces.IExternalObject )

	def toExternalObject(self):
		result = super(_HighlightExternalObject, self).toExternalObject()
		result[SNIPPET] = get_content(get_attr(self.entity, [startHighlightedFullText_]))
		return result
	
class _NoteExternalObject(_MixinExternalObject):
	component.adapts( nti_interfaces.INote )
	interface.implements( nti_interfaces.IExternalObject )

	def toExternalObject(self):
		result = super(_NoteExternalObject, self).toExternalObject()
		result[SNIPPET] = get_multipart_content(get_attr(self.entity, [body_]))
		return result
	
class _MessageInfoExternalObject(_MixinExternalObject):
	component.adapts( chat_interfaces.IMessageInfo )
	interface.implements( nti_interfaces.IExternalObject )

	def toExternalObject(self):
		result = super(_MessageInfoExternalObject, self).toExternalObject()
		result[TYPE] = MESSAGE_INFO
		result[ID] = get_attr(self.entity, [ID])
		result[SNIPPET] = get_multipart_content(get_attr(self.entity, [BODY]))
		return result

def _adapt_to_search_hit(adapter, query, highlight_type=WORD_HIGHLIGHT, *args, **kwargs):
	result = adapter.toExternalObject() if adapter else None
	if result:
		text = result[SNIPPET]
		result[SNIPPET] = _highlight_content(query,text,highlight_type,*args, **kwargs)
	return result

def get_search_hit(obj, query=None, highlight_type=WORD_HIGHLIGHT, *args, **kwargs):
	adapter = component.queryAdapter( obj, nti_interfaces.IExternalObject, default=None, name='search-hit')
	result = _adapt_to_search_hit(adapter, query, highlight_type, *args, **kwargs)
	return result

