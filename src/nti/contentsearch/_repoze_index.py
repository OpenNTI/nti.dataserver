from __future__ import print_function, unicode_literals

import six
import BTrees
from collections import Iterable

from zope.index.text.baseindex import BaseIndex

from repoze.catalog.catalog import Catalog
from repoze.catalog.indexes.common import CatalogIndex
from repoze.catalog.indexes.field import CatalogFieldIndex
from repoze.catalog.indexes.keyword import CatalogKeywordIndex

from nti.contentsearch._content_utils import get_content
from nti.contentsearch._content_utils import get_note_content
from nti.contentsearch._content_utils import get_highlight_content
from nti.contentsearch._content_utils import get_redaction_content
from nti.contentsearch._content_utils import get_messageinfo_content

from nti.contentsearch.common import ngrams
from nti.contentsearch.common import get_attr
from nti.contentsearch.common import get_ntiid
from nti.contentsearch.common import get_creator
from nti.contentsearch.common import get_references
from nti.contentsearch.common import get_external_oid
from nti.contentsearch.common import get_last_modified
from nti.contentsearch.common import normalize_type_name
from nti.contentsearch.textindexng3 import CatalogTextIndexNG3

from nti.contentsearch.common import (	container_id_fields, keyword_fields)

from nti.contentsearch.common import (	OID, NTIID, CREATOR, LAST_MODIFIED, CONTAINER_ID, COLLECTION_ID, ID)

from nti.contentsearch.common import (	ngrams_, channel_, content_, keywords_, references_, title_, 
										last_modified_, section_, ntiid_, recipients_, sharedWith_,  
										related_,  note_, highlight_, messageinfo_, replacementContent_,
										redactionExplanation_, redaction_)


import logging
logger = logging.getLogger( __name__ )

# want to make sure change the family for all catalog index fields
BaseIndex.family = BTrees.family64
CatalogIndex.family = BTrees.family64

#TODO: set this as part of a config
compute_ngrams = False 

def _get_text(obj, names):
	result = obj if isinstance(obj, six.string_types) else get_attr(obj, names)
	return unicode(result) if result else None

def get_id(obj, default=None):
	return _get_text(obj, [ID])

def get_title(obj, default=None):
	return _get_text(obj, [title_])

def get_section(obj, default=None):
	return _get_text(obj, [section_])

def get_channel(obj, default=None):
	return _get_text(obj, [channel_])

def get_containerId(obj, default=None):
	return _get_text(obj, container_id_fields)

def get_none(obj, default=None):
	return None

# restore for backward comp
get_oid = get_external_oid
get_objectId = get_external_oid

def _parse_words(obj, fields, default=None):
	words = obj if isinstance(obj, six.string_types) else get_attr(obj, fields)
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

def get_related(obj, default=None):
	return _parse_words(obj, [related_])

def get_note_ngrams(obj, default=None):
	return ngrams(get_note_content(obj)) if compute_ngrams else u''
		
def get_highlight_ngrams(obj, default=None):
	return ngrams(get_highlight_content(obj)) if compute_ngrams else u''

def get_redaction_ngrams(obj, default=None):
	return ngrams(get_redaction_content(obj)) if compute_ngrams else u''

def get_messageinfo_ngrams(obj, default=None):
	return ngrams(get_messageinfo_content(obj)) if compute_ngrams else u''

def get_replacement_content(obj, default=None):
	source = _get_text(obj, [replacementContent_])
	result = get_content(source) if source else None
	return result.lower() if result else None
	
def get_redaction_explanation(obj, default=None):
	source = _get_text(obj, [redactionExplanation_])
	result = get_content(source) if source else None
	return result.lower() if result else None
	
def _create_text_index(field, discriminator):
	return CatalogTextIndexNG3(field, discriminator)

def _create_treadable_mixin_catalog():
	catalog = Catalog(family=BTrees.family64)
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

def create_redaction_catalog():
	catalog = _create_treadable_mixin_catalog()
	catalog[ngrams_] = _create_text_index(ngrams_, get_redaction_ngrams)
	catalog[content_] = _create_text_index(content_, get_redaction_content)
	catalog[replacementContent_] = _create_text_index(replacementContent_, get_replacement_content)
	catalog[redactionExplanation_] = _create_text_index(redactionExplanation_, get_redaction_explanation)
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

def create_book_catalog():
	catalog = Catalog(family=BTrees.family64)
	catalog[ntiid_] = CatalogFieldIndex(get_ntiid)
	catalog[title_] = CatalogFieldIndex(get_title)
	catalog[last_modified_] = CatalogFieldIndex(get_last_modified)
	catalog[keywords_] = CatalogKeywordIndex(get_keywords)
	catalog[related_] = CatalogKeywordIndex(get_related)
	catalog[ngrams_] = _create_text_index(ngrams_, get_messageinfo_ngrams)
	catalog[content_] = _create_text_index(content_, get_messageinfo_content)
	catalog[section_] = CatalogFieldIndex(get_section)
	return catalog

def create_catalog(type_name=note_):
	type_name = normalize_type_name(type_name)
	if type_name == note_:
		return create_notes_catalog()
	elif type_name == highlight_:
		return create_highlight_catalog()
	elif type_name == redaction_:
		return create_redaction_catalog()
	elif type_name == messageinfo_:
		return create_messageinfo_catalog()
	else:
		return None

