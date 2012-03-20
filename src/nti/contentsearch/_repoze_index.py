from datetime import datetime
from collections import Iterable

from repoze.catalog.catalog import Catalog
from repoze.catalog.indexes.field import CatalogFieldIndex
from repoze.catalog.indexes.keyword import CatalogKeywordIndex

from nti.contentsearch.common import ngrams
from nti.contentsearch.common import get_attr
from nti.contentsearch.common import epoch_time
from nti.contentsearch.common import get_content
from nti.contentsearch.common import get_type_name
from nti.contentsearch.common import get_collection
from nti.contentsearch.common import get_multipart_content
from nti.contentsearch.common import word_content_highlight
from nti.contentsearch.common import ngram_content_highlight
from nti.contentsearch.textindexng3 import CatalogTextIndexNG3

from nti.contentsearch.common import (	oid_fields, ntiid_fields, creator_fields, container_id_fields,
										last_modified_fields, keyword_fields)

from nti.contentsearch.common import (	OID, NTIID, CREATOR, LAST_MODIFIED, CONTAINER_ID, CLASS, TYPE,
										COLLECTION_ID, SNIPPET, HIT, ID, BODY, TARGET_OID)

from nti.contentsearch.common import (	ngrams_, channel_, content_, keywords_, references_, 
										recipients_, sharedWith_, body_, startHighlightedFullText_)


import logging
logger = logging.getLogger( __name__ )

# -----------------------------------

def get_last_modified(obj, default=None):
	value  = get_attr(obj, last_modified_fields, default)
	if value:
		if isinstance(value, basestring):
			value = float(value)
		elif isinstance(value, datetime):
			value = epoch_time(value)
	else:
		value = 0
	return value

# -----------------------------------

def get_id(obj, default=None):
	return obj if isinstance(obj, basestring) else get_attr(obj, [ID])

def get_channel(obj, default=None):
	return obj if isinstance(obj, basestring) else get_attr(obj, [channel_])

def get_objectId(obj, default=None):
	return obj if isinstance(obj, basestring) else get_attr(obj, oid_fields)
get_oid = get_objectId

def get_containerId(obj, default=None):
	return obj if isinstance(obj, basestring) else get_attr(obj, container_id_fields)

def get_collectionId(obj, default=None):
	containerId = get_containerId(obj, default)
	return get_collection(containerId)

def get_creator(obj, default=None):
	return obj if isinstance(obj, basestring) else get_attr(obj, creator_fields)

def get_ntiid(obj, default=None):
	return obj if isinstance(obj, basestring) else get_attr(obj, ntiid_fields)

# -----------------------------------

def _parse_words(obj, fields, default=None):
	words = obj if isinstance(obj, basestring) else get_attr(obj, fields, default)
	if words:
		if isinstance(words, basestring):
			words = words.lower().split()
		elif isinstance(words, Iterable):
			words = [w.lower() for w in words]
		else:
			words = [words.lower()]
	return words
	
def get_keywords(obj, default=None):
	result = set()
	for name in keyword_fields:
		words =  _parse_words(obj, [name])
		if words:
			result.update(words)
	return result if result else None

def get_references(obj, default=None):
	return _parse_words(obj, [references_])

def get_recipients(obj, default=None):
	return _parse_words(obj, [recipients_])

def get_sharedWith(obj, default=None):
	return _parse_words(obj, [sharedWith_])

# -----------------------------------

def get_note_ngrams(obj, default=None):
	source = obj if isinstance(obj, basestring) else get_attr(obj, [body_], default)
	result = ngrams(get_multipart_content(source))
	return result
	
def get_note_content(obj, default=None):
	source = obj if isinstance(obj, basestring) else get_attr(obj, [body_], default)
	result = get_multipart_content(source)
	return result.lower() if result else None
	
def get_highlight_ngrams(obj, default=None):
	source = obj if isinstance(obj, basestring) else get_attr(obj, [startHighlightedFullText_], default)
	result = ngrams(get_multipart_content(source))
	return result
	
def get_highlight_content(obj, default=None):
	source = obj if isinstance(obj, basestring) else get_attr(obj, [startHighlightedFullText_], default)
	result = get_content(source)
	return result.lower() if result else None

def get_messageinfo_ngrams(obj, default=None):
	source = obj if isinstance(obj, basestring) else get_attr(obj, [BODY], default)
	result = ngrams(get_multipart_content(source))
	return result
	
def get_messageinfo_content(obj, default=None):
	source = obj if isinstance(obj, basestring) else get_attr(obj, [BODY], default)
	result = get_multipart_content(source)
	return result.lower() if result else None

# -----------------------------------

def _create_text_index(field, discriminator):
	return CatalogTextIndexNG3(field, discriminator)

def _create_treadable_mixin_catalog():
	catalog = Catalog()
	catalog[NTIID] = CatalogFieldIndex(get_ntiid)
	catalog[OID] = CatalogFieldIndex(get_objectId)
	catalog[CREATOR] = CatalogFieldIndex(get_creator)
	catalog[keywords_] = CatalogKeywordIndex(get_keywords)
	catalog[sharedWith_] = CatalogKeywordIndex(get_sharedWith)
	catalog[CONTAINER_ID] = CatalogFieldIndex(get_containerId)
	catalog[COLLECTION_ID] = CatalogFieldIndex(get_collectionId)
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
	type_name = type_name[0:-1] if type_name.endswith('s') else type_name
	type_name = type_name.lower()
	if type_name == 'note':
		return create_notes_catalog()
	elif type_name == 'highlight':
		return create_highlight_catalog()
	elif type_name =='messageinfo':
		return create_messageinfo_catalog()
	else:
		raise None
	
# -----------------------------------
		
def _get_last_modified(obj):
	lm = get_attr(obj, last_modified_fields )
	return lm if lm else 0

def _word_content_highlight(query=None, text=None, *args, **kwargs):
	content = word_content_highlight(query, text, *args, **kwargs) if query and text else u''
	return unicode(content) if content else text

def _ngram_content_highlight(query=None, text=None, *args, **kwargs):
	content = ngram_content_highlight(query, text, *args, **kwargs) if query and text else u''
	return unicode(content) if content else text

def _highlight_content(query=None, text=None, use_word_highlight=True, *args, **kwargs):
	content = None
	if query and text:
		content = 	_word_content_highlight(query, text, *args, **kwargs) if use_word_highlight else \
					_ngram_content_highlight(query, text, *args, **kwargs)
	return unicode(content) if content else text

def _get_index_hit_from_object(obj):
	result = {TYPE : get_type_name(obj), CLASS:HIT}		
	result[TARGET_OID] =  get_attr(obj, oid_fields )
	result[NTIID] =  get_attr(obj, ntiid_fields )
	result[CREATOR] =  get_attr(obj, creator_fields )
	result[CONTAINER_ID] = get_attr(obj, container_id_fields )
	result[COLLECTION_ID] = get_collection(result[CONTAINER_ID])
	result[LAST_MODIFIED] = _get_last_modified(obj)
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
	result[SNIPPET] = _highlight_content(unicode(query), unicode(text), use_word_highlight, *args, **kwargs)
	return result

def get_index_hit(obj, query=None, use_word_highlight=True, *args, **kwargs):
	type_name =  get_type_name(obj)
	if type_name == 'note':
		return get_index_hit_from_note(obj, query, use_word_highlight, *args, **kwargs)
	elif type_name == 'highlight':
		return get_index_hit_from_hightlight(obj, query, use_word_highlight, *args, **kwargs)
	elif type_name =='messageinfo':
		return get_index_hit_from_messgeinfo(obj, query, use_word_highlight, *args, **kwargs)
	else:
		return None
	
