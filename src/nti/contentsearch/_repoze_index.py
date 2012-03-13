from datetime import datetime
from collections import Iterable

from repoze.catalog.catalog import Catalog
from repoze.catalog.indexes.field import CatalogFieldIndex
from repoze.catalog.indexes.keyword import CatalogKeywordIndex

from nti.dataserver.chat import MessageInfo
from nti.dataserver.contenttypes import Note
from nti.dataserver.contenttypes import Canvas
from nti.dataserver.contenttypes import Highlight

from nti.contentsearch.common import ngrams
from nti.contentsearch.common import to_list
from nti.contentsearch.common import epoch_time
from nti.contentsearch.common import get_content
from nti.contentsearch.common import get_collection
from nti.contentsearch.common import word_content_highlight
from nti.contentsearch.common import ngram_content_highlight
from nti.contentsearch.textindexng3 import CatalogTextIndexNG3
from nti.contentsearch.common import (	OID, NTIID, CREATOR, LAST_MODIFIED, CONTAINER_ID, CLASS, TYPE, \
										COLLECTION_ID, ITEMS, SNIPPET, ID)

from nti.contentsearch.common import (	color_, ngrams_, channel_, content_, keywords_, references_, \
										recipients_, sharedWith_ )


import logging
logger = logging.getLogger( __name__ )

# -----------------------------------
	
def get_attr(obj, names, default=None):
	if not obj: return default
	
	names = to_list(names)
	if isinstance(obj, dict):
		for name in names:
			value = obj.get(name,None)
			if value: return value
	else:
		for name in names:
			try:
				value = getattr(obj, name, None)
			except:
				value = None
			if value: return value
	return default

def _attrs(names):
	lexp = lambda x,y: get_attr(x, names,y)
	return lexp

# -----------------------------------

_oid_fields = [OID, 'oid', 'id']
_ntiid_fields = [NTIID, 'ntiid']
_creator_fields = [CREATOR, 'creator']
_container_id_fields = [CONTAINER_ID, 'ContainerId', 'containerId', 'container']
_last_modified_fields =  [LAST_MODIFIED, 'lastModified', 'LastModified', 'last_modified']

def _last_modified(obj, default):
	value  = get_attr(obj, _last_modified_fields, default)
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
	containerId = get_attr(obj, _container_id_fields, default)
	return get_collection(containerId)

def get_objectId(data):
	return data if isinstance(data, basestring) else get_attr(data, _oid_fields)

# -----------------------------------

def _content(names):
	def f(obj, default):
		value = get_attr(obj, names, default)
		value = get_content(value)
		return value
	return f

def get_multipart_content(source):
	
	gbls = globals()
			
	if isinstance(source, basestring):
		return get_content(source)
	elif isinstance(source, Iterable):
		
		def process_dict(d):
			clazz = item.get(CLASS, None)
			data = item.get(ITEMS, None)
			if clazz and data:
				name = "get_%s_content" % clazz.lower()
				if name in gbls:
					return gbls[name](d)
			return u''
		
		items = []
		if isinstance(source, dict):
			items.append(process_dict(source))
		else:
			for item in source:
				if isinstance(item, basestring) and item:
					items.append(item)
					continue
				elif isinstance(item, dict):
					items.append(process_dict(item))
				else:
					items.add(get_multipart_content(item))
		return get_content(' '.join(items))
	elif not source:
		clazz = source.__class__.__name__
		name = "get_%s_content" % clazz.lower()
		if name in gbls:
			return gbls[name](source)
	return u''

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

_body = 'body'
_startHighlightedFullText = 'startHighlightedFullText'

def get_highlight_content(data):
	if isinstance(data, dict):
		return data.get(_startHighlightedFullText, u'')
	elif isinstance(data, Highlight):
		return getattr(data, _startHighlightedFullText, u'')
	return u''

def get_canvas_content(data):
	result = []
	if isinstance(data, dict):
		shapes = data.get('shapeList', [])
	elif isinstance(data, Canvas):
		shapes = data.shapeList
		
	for s in shapes:
		c = get_multipart_content(s)
		if c: result.append(c)
	return ' '.join(result)

def get_note_content(data):
	result = []
	if isinstance(data, dict):
		body = to_list(data.get(_body, u''))
	elif isinstance(data, Note):
		body = to_list(data.body)
		
	for item in body:
		c = get_multipart_content(item)
		if c: result.append(c)
	return ' '.join(result)

def get_messageinfo_content(data):
	result = []
	if isinstance(data, dict):
		body = to_list(data.get(_body, u''))
	elif isinstance(data, MessageInfo):
		body = to_list(data.body)
	for item in body:
		c = get_multipart_content(item)
		if c: result.append(c)
	return ' '.join(result)

# -----------------------------------

def _create_text_index(field, discriminator):
	return CatalogTextIndexNG3(field, discriminator)

def _create_treadable_mixin_catalog():
	catalog = Catalog()
	catalog[LAST_MODIFIED] = CatalogFieldIndex(_last_modified)
	catalog[OID] = CatalogFieldIndex(_attrs(_oid_fields))
	catalog[CONTAINER_ID] = CatalogFieldIndex(_attrs(_container_id_fields))
	catalog[COLLECTION_ID] = CatalogFieldIndex(_collectionId)
	catalog[CREATOR] = CatalogFieldIndex(_attrs(_creator_fields))
	catalog[NTIID] = CatalogFieldIndex(_attrs(_ntiid_fields))
	catalog[keywords_] = CatalogKeywordIndex(_keywords([keywords_]))
	catalog[sharedWith_] = CatalogKeywordIndex(_keywords([sharedWith_]))
	return catalog

def create_notes_catalog():
	catalog = _create_treadable_mixin_catalog()
	catalog[ngrams_] = _create_text_index(ngrams_, _ngrams([_body]))
	catalog[references_] = CatalogKeywordIndex(_keywords([references_]))
	catalog[content_] = _create_text_index(content_, _multipart_content([_body]))
	return catalog
	
def create_highlight_catalog():
	catalog = _create_treadable_mixin_catalog()
	catalog[color_] = CatalogFieldIndex(_attrs([color_]))
	catalog[ngrams_] = _create_text_index(ngrams_, _ngrams([_startHighlightedFullText]))
	catalog[content_] = _create_text_index(content_, _content([_startHighlightedFullText]))
	return catalog

def create_messageinfo_catalog():
	catalog = _create_treadable_mixin_catalog()
	catalog[ID] = CatalogFieldIndex(_attrs([ID]))
	catalog[channel_] = CatalogFieldIndex(_attrs([channel_]))
	catalog[ngrams_] = _create_text_index(ngrams_, _ngrams([_body]))
	catalog[content_] = _create_text_index(content_, _multipart_content([_body]))
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
	lm = get_attr(obj, _last_modified_fields )
	return lm if lm else 0

def _word_content_highlight(query=None, text=None,  *args, **kwargs):
	content = word_content_highlight(query, text) if query and text else u''
	return content if content else text

def _ngram_content_highlight(query=None, text=None, *args, **kwargs):
	content = ngram_content_highlight(query, text,  *args, **kwargs) if query and text else u''
	return content if content else text

def _highlight_content(query=None, text=None, use_word_highlight=True):
	content = None
	if query and text:
		content = 	word_content_highlight(query, text) if use_word_highlight else \
					_ngram_content_highlight(query, text)
	return content if content else text

def _get_index_hit_from_object(obj):
	result = {TYPE : get_type_name(obj)}		
	result[OID] =  get_attr(obj, _oid_fields )
	result[NTIID] =  get_attr(obj, _ntiid_fields )
	result[CREATOR] =  get_attr(obj, _creator_fields )
	result[CONTAINER_ID] = get_attr(obj, _container_id_fields )
	result[COLLECTION_ID] = get_collection(result[CONTAINER_ID])
	result[LAST_MODIFIED] = _get_last_modified(obj)
	return result

def get_index_hit_from_note(obj, query=None, use_word_highlight=True, *args, **kwargs):
	text = get_attr(obj, [_body])
	result = _get_index_hit_from_object(obj)
	result[SNIPPET] = _highlight_content(query, text, use_word_highlight)
	return result

def get_index_hit_from_hightlight(obj, query=None, use_word_highlight=True, *args, **kwargs):
	result = _get_index_hit_from_object(obj)
	text = get_attr(obj, [_startHighlightedFullText])
	result[SNIPPET] = _highlight_content(query, text, use_word_highlight)
	return result

def get_index_hit_from_messgeinfo(obj, query=None, use_word_highlight=True, *args, **kwargs):
	text = get_attr(obj, [_body])
	result = _get_index_hit_from_object(obj)
	result[SNIPPET] = _highlight_content(query, text, use_word_highlight)
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
	
