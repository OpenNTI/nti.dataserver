import six
from datetime import datetime
from collections import Iterable

from repoze.catalog.catalog import Catalog
from repoze.catalog.indexes.field import CatalogFieldIndex
from repoze.catalog.indexes.keyword import CatalogKeywordIndex

from nti.contentsearch.common import ngrams
from nti.contentsearch.common import get_attr
from nti.contentsearch.common import get_ntiid
from nti.contentsearch.common import epoch_time
from nti.contentsearch.common import get_content
from nti.contentsearch.common import get_creator
from nti.contentsearch.common import get_type_name
from nti.contentsearch.common import get_collection
from nti.contentsearch.common import get_references
from nti.contentsearch.common import get_external_oid
from nti.contentsearch.common import normalize_type_name
from nti.contentsearch.common import get_multipart_content
from nti.contentsearch.common import word_content_highlight
from nti.contentsearch.common import ngram_content_highlight
from nti.contentsearch.textindexng3 import CatalogTextIndexNG3

from nti.contentsearch.common import (	oid_fields, container_id_fields, last_modified_fields, keyword_fields)

from nti.contentsearch.common import (	OID, NTIID, CREATOR, LAST_MODIFIED, CONTAINER_ID, CLASS, TYPE,
										COLLECTION_ID, SNIPPET, HIT, ID, BODY, TARGET_OID, MESSAGE_INFO)

from nti.contentsearch.common import (	ngrams_, channel_, content_, keywords_, references_, 
										recipients_, sharedWith_, body_, startHighlightedFullText_)


import logging
logger = logging.getLogger( __name__ )

# -----------------------------------

def get_last_modified(obj, default=None):
	value = get_attr(obj, last_modified_fields, default)
	if value:
		if isinstance(value, six.string_types):
			value = float(value)
		elif isinstance(value, datetime):
			value = epoch_time(value)
	else:
		value = 0
	return value

# -----------------------------------

def get_id(obj, default=None):
	result = obj if isinstance(obj, six.string_types) else get_attr(obj, [ID])
	return unicode(result) if result else None

def get_channel(obj, default=None):
	result = obj if isinstance(obj, six.string_types) else get_attr(obj, [channel_])
	return unicode(result) if result else None

def get_objectId(obj, default=None):
	result = obj if isinstance(obj, six.string_types) else get_attr(obj, oid_fields)
	return unicode(result) if result else None
get_oid = get_objectId

def get_containerId(obj, default=None):
	result = obj if isinstance(obj, six.string_types) else get_attr(obj, container_id_fields)
	return unicode(result) if result else None

def get_collectionId(obj, default=None):
	containerId = get_containerId(obj, default)
	return get_collection(containerId) if containerId else None

def get_none(obj, default=None):
	return None

# -----------------------------------

def _parse_words(obj, fields, default=None):
	words = obj if isinstance(obj, six.string_types) else get_attr(obj, fields, default)
	if words:
		if isinstance(words, six.string_types):
			words = [unicode(w.lower()) for w in words.split()]
		elif isinstance(words, Iterable):
			words = [unicode(w.lower()) for w in words]
		else:
			words = []
	return words or []
	
def get_keywords(obj, default=None):
	result = set()
	for name in keyword_fields:
		words =  _parse_words(obj, [name])
		if words:
			result.update(words)
	return result if result else []

def get_recipients(obj, default=None):
	return _parse_words(obj, [recipients_])

def get_sharedWith(obj, default=None):
	return _parse_words(obj, [sharedWith_])

# -----------------------------------

def get_note_ngrams(obj, default=None):
	source = obj if isinstance(obj, six.string_types) else get_attr(obj, [body_], default)
	result = ngrams(get_multipart_content(source))
	return result
	
def get_note_content(obj, default=None):
	source = obj if isinstance(obj, six.string_types) else get_attr(obj, [body_], default)
	result = get_multipart_content(source)
	return result.lower() if result else None
	
def get_highlight_ngrams(obj, default=None):
	source = obj if isinstance(obj, six.string_types) else get_attr(obj, [startHighlightedFullText_], default)
	result = ngrams(get_multipart_content(source))
	return result
	
def get_highlight_content(obj, default=None):
	source = obj if isinstance(obj, six.string_types) else get_attr(obj, [startHighlightedFullText_], default)
	result = get_content(source)
	return result.lower() if result else None

def get_messageinfo_ngrams(obj, default=None):
	source = obj if isinstance(obj, six.string_types) else get_attr(obj, [BODY], default)
	result = ngrams(get_multipart_content(source))
	return result
	
def get_messageinfo_content(obj, default=None):
	source = obj if isinstance(obj, six.string_types) else get_attr(obj, [BODY], default)
	result = get_multipart_content(source)
	return result.lower() if result else None

# -----------------------------------

def _create_text_index(field, discriminator):
	return CatalogTextIndexNG3(field, discriminator)

def _create_treadable_mixin_catalog():
	catalog = Catalog()
	catalog[NTIID] = CatalogFieldIndex(get_ntiid)
	catalog[OID] = CatalogFieldIndex(get_external_oid)
	catalog[CREATOR] = CatalogFieldIndex(get_creator)
	catalog[keywords_] = CatalogKeywordIndex(get_keywords)
	catalog[sharedWith_] = CatalogKeywordIndex(get_sharedWith)
	catalog[CONTAINER_ID] = CatalogFieldIndex(get_containerId)
	catalog[COLLECTION_ID] = CatalogFieldIndex(get_none)
	catalog[LAST_MODIFIED] = CatalogFieldIndex(get_last_modified)
	return catalog

def create_notes_catalog():
	catalog = _create_treadable_mixin_catalog()
	catalog[references_] = CatalogKeywordIndex(get_references)
	catalog[ngrams_] = _create_text_index(ngrams_, get_note_ngrams)
	catalog[content_] = _create_text_index(content_, get_note_content)
	return catalog
	
def create_highlight_catalog():
	catalog = _create_treadable_mixin_catalog()
	catalog[ngrams_] = _create_text_index(ngrams_, get_highlight_ngrams)
	catalog[content_] = _create_text_index(content_, get_highlight_content)
	return catalog

def create_messageinfo_catalog():
	catalog = _create_treadable_mixin_catalog()
	catalog[ID] = CatalogFieldIndex(get_id)
	catalog[channel_] = CatalogFieldIndex(get_channel)
	catalog[recipients_] = CatalogKeywordIndex(get_recipients)
	catalog[references_] = CatalogKeywordIndex(get_references)
	catalog[ngrams_] = _create_text_index(ngrams_, get_messageinfo_ngrams)
	catalog[content_] = _create_text_index(content_, get_messageinfo_content)
	return catalog

def create_catalog(type_name='Notes'):
	type_name = normalize_type_name(type_name)
	if type_name == 'note':
		return create_notes_catalog()
	elif type_name == 'highlight':
		return create_highlight_catalog()
	elif type_name =='messageinfo':
		return create_messageinfo_catalog()
	else:
		return None
	
# -----------------------------------

def _word_content_highlight(query=None, text=None, *args, **kwargs):
	content = word_content_highlight(query, text, *args, **kwargs) if query and text else u''
	return unicode(content) if content else text

def _ngram_content_highlight(query=None, text=None, *args, **kwargs):
	content = ngram_content_highlight(query, text, *args, **kwargs) if query and text else u''
	return unicode(content) if content else text

def _highlight_content(query=None, text=None, use_word_highlight=True, *args, **kwargs):
	content = None
	if query and text and use_word_highlight is not None:
		content = 	_word_content_highlight(query, text, *args, **kwargs) if use_word_highlight else \
					_ngram_content_highlight(query, text, *args, **kwargs)
	return unicode(content) if content else text

def _get_index_hit_from_object(obj):
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

def get_index_hit_from_note(obj, query=None, use_word_highlight=True, *args, **kwargs):
	text = get_multipart_content(get_attr(obj, [body_]))
	result = _get_index_hit_from_object(obj)
	result[SNIPPET] = _highlight_content(unicode(query), unicode(text), use_word_highlight, *args, **kwargs)
	return result

def get_index_hit_from_hightlight(obj, query=None, use_word_highlight=True, *args, **kwargs):
	result = _get_index_hit_from_object(obj)
	text = get_content(get_attr(obj, [startHighlightedFullText_]))
	result[SNIPPET] = _highlight_content(unicode(query), unicode(text), use_word_highlight, *args, **kwargs)
	return result

def get_index_hit_from_messgeinfo(obj, query=None, use_word_highlight=True, *args, **kwargs):
	text = get_multipart_content(get_attr(obj, [BODY]))
	result = _get_index_hit_from_object(obj)
	result[TYPE] = MESSAGE_INFO
	result[ID] = get_attr(obj, [ID])
	result[SNIPPET] = _highlight_content(unicode(query), unicode(text), use_word_highlight, *args, **kwargs)
	return result

def get_index_hit(obj, query=None, use_word_highlight=True, *args, **kwargs):
	result = None
	if obj is not None:
		type_name = get_type_name(obj)
		if type_name == 'note':
			result = get_index_hit_from_note(obj, query, use_word_highlight, *args, **kwargs)
		elif type_name == 'highlight':
			result = get_index_hit_from_hightlight(obj, query, use_word_highlight, *args, **kwargs)
		elif type_name =='messageinfo':
			result = get_index_hit_from_messgeinfo(obj, query, use_word_highlight, *args, **kwargs)
	return result
	
