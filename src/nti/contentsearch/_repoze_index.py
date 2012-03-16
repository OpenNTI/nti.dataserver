from datetime import datetime
from collections import Iterable

from repoze.catalog.catalog import Catalog
from repoze.catalog.indexes.field import CatalogFieldIndex
from repoze.catalog.indexes.keyword import CatalogKeywordIndex

from nti.contentsearch.common import ngrams
from nti.contentsearch.common import get_attr
from nti.contentsearch.common import epoch_time
from nti.contentsearch.common import get_content
from nti.contentsearch.common import get_collection
from nti.contentsearch.common import get_multipart_content
from nti.contentsearch.common import word_content_highlight
from nti.contentsearch.common import ngram_content_highlight
from nti.contentsearch.textindexng3 import CatalogTextIndexNG3

from nti.contentsearch.common import (	oid_fields, ntiid_fields, creator_fields, container_id_fields,
										last_modified_fields)

from nti.contentsearch.common import (	OID, NTIID, CREATOR, LAST_MODIFIED, CONTAINER_ID, CLASS, TYPE,
										COLLECTION_ID, SNIPPET, HIT, ID)

from nti.contentsearch.common import (	color_, ngrams_, channel_, content_, keywords_, references_,
										recipients_, sharedWith_, body_, startHighlightedFullText_)


import logging
logger = logging.getLogger( __name__ )

# -----------------------------------
	
def _attrs(names):
	lexp = lambda x,y: get_attr(x, names,y)
	return lexp

# -----------------------------------

def _last_modified(obj, default):
	value  = get_attr(obj, last_modified_fields, default)
	if value:
		if isinstance(value, basestring):
			value = float(value)
		elif isinstance(value, datetime):
			value = epoch_time(value)
	else:
		value = 0
	return value

def _keywords(names):
	def f(obj, default):
		words  = get_attr(obj, names, default)
		if words:
			if isinstance(words, basestring):
				words = words.split()
			elif isinstance(words, Iterable):
				words = [w for w in words]
			else:
				words = [words]
		return words
	return f
	
def _collectionId(obj, default):
	containerId = get_attr(obj, container_id_fields, default)
	return get_collection(containerId)

def get_objectId(data):
	return data if isinstance(data, basestring) else get_attr(data, oid_fields)

# -----------------------------------

def _content(names):
	def f(obj, default):
		value = get_attr(obj, names, default)
		value = get_content(value)
		return value
	return f

def _multipart_content(names):
	def f(obj, default):
		source = get_attr(obj, names, default)
		result = get_multipart_content(source)
		return result
	return f

def _ngrams(names):
	def f(obj, default):
		source = get_attr(obj, names, default)
		result = ngrams(get_multipart_content(source))
		return result
	return f

# -----------------------------------

def _create_text_index(field, discriminator):
	return CatalogTextIndexNG3(field, discriminator)

def _create_treadable_mixin_catalog():
	catalog = Catalog()
	catalog[LAST_MODIFIED] = CatalogFieldIndex(_last_modified)
	catalog[OID] = CatalogFieldIndex(_attrs(oid_fields))
	catalog[CONTAINER_ID] = CatalogFieldIndex(_attrs(container_id_fields))
	catalog[COLLECTION_ID] = CatalogFieldIndex(_collectionId)
	catalog[CREATOR] = CatalogFieldIndex(_attrs(creator_fields))
	catalog[NTIID] = CatalogFieldIndex(_attrs(ntiid_fields))
	catalog[keywords_] = CatalogKeywordIndex(_keywords([keywords_]))
	catalog[sharedWith_] = CatalogKeywordIndex(_keywords([sharedWith_]))
	return catalog

def create_notes_catalog():
	catalog = _create_treadable_mixin_catalog()
	catalog[ngrams_] = _create_text_index(ngrams_, _ngrams([body_]))
	catalog[references_] = CatalogKeywordIndex(_keywords([references_]))
	catalog[content_] = _create_text_index(content_, _multipart_content([body_]))
	return catalog
	
def create_highlight_catalog():
	catalog = _create_treadable_mixin_catalog()
	catalog[color_] = CatalogFieldIndex(_attrs([color_]))
	catalog[ngrams_] = _create_text_index(ngrams_, _ngrams([startHighlightedFullText_]))
	catalog[content_] = _create_text_index(content_, _content([startHighlightedFullText_]))
	return catalog

def create_messageinfo_catalog():
	catalog = _create_treadable_mixin_catalog()
	catalog[ID] = CatalogFieldIndex(_attrs([ID]))
	catalog[channel_] = CatalogFieldIndex(_attrs([channel_]))
	catalog[ngrams_] = _create_text_index(ngrams_, _ngrams([body_]))
	catalog[content_] = _create_text_index(content_, _multipart_content([body_]))
	catalog[references_] = CatalogKeywordIndex(_keywords([references_]))
	catalog[recipients_] = CatalogKeywordIndex(_keywords([recipients_]))
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

def get_type_name(obj):
	if not isinstance(obj, dict):
		return obj.__class__.__name__
	else:
		return get_attr(obj, [CLASS])
		
def _get_last_modified(obj):
	lm = get_attr(obj, last_modified_fields )
	return lm if lm else 0

def _word_content_highlight(query=None, text=None, **kwargs):
	content = word_content_highlight(query, text) if query and text else u''
	return content if content else text

def _ngram_content_highlight(query=None, text=None, **kwargs):
	content = ngram_content_highlight(query, text, **kwargs) if query and text else u''
	return content if content else text

def _highlight_content(query=None, text=None, use_word_highlight=True):
	content = None
	if query and text:
		content = 	word_content_highlight(query, text) if use_word_highlight else \
					_ngram_content_highlight(query, text)
	return content if content else text

def _get_index_hit_from_object(obj):
	result = {TYPE : get_type_name(obj), CLASS:HIT}		
	result[OID] =  get_attr(obj, oid_fields )
	result[NTIID] =  get_attr(obj, ntiid_fields )
	result[CREATOR] =  get_attr(obj, creator_fields )
	result[CONTAINER_ID] = get_attr(obj, container_id_fields )
	result[COLLECTION_ID] = get_collection(result[CONTAINER_ID])
	result[LAST_MODIFIED] = _get_last_modified(obj)
	return result

def get_index_hit_from_note(obj, query=None, use_word_highlight=True, **kwargs):
	text = get_attr(obj, [body_])
	result = _get_index_hit_from_object(obj)
	result[SNIPPET] = _highlight_content(query, text, use_word_highlight)
	return result

def get_index_hit_from_hightlight(obj, query=None, use_word_highlight=True, **kwargs):
	result = _get_index_hit_from_object(obj)
	text = get_attr(obj, [startHighlightedFullText_])
	result[SNIPPET] = _highlight_content(query, text, use_word_highlight)
	return result

def get_index_hit_from_messgeinfo(obj, query=None, use_word_highlight=True, **kwargs):
	text = get_attr(obj, [body_])
	result = _get_index_hit_from_object(obj)
	result[SNIPPET] = _highlight_content(query, text, use_word_highlight)
	return result

def get_index_hit(obj, query=None, use_word_highlight=True, **kwargs):
	type_name =  get_type_name(obj)
	if type_name == 'note':
		return get_index_hit_from_note(obj, query, use_word_highlight, **kwargs)
	elif type_name == 'highlight':
		return get_index_hit_from_hightlight(obj, query, use_word_highlight, **kwargs)
	elif type_name =='messageinfo':
		return get_index_hit_from_messgeinfo(obj, query, use_word_highlight, **kwargs)
	else:
		return None
	
