from __future__ import print_function, unicode_literals

import BTrees

from zope import component
from zope.index.text.baseindex import BaseIndex

from repoze.catalog.catalog import Catalog
from repoze.catalog.indexes.common import CatalogIndex
from repoze.catalog.indexes.field import CatalogFieldIndex
from repoze.catalog.indexes.keyword import CatalogKeywordIndex

from nti.contentsearch import compute_ngrams
from nti.contentsearch.interfaces import IContentResolver
from nti.contentsearch.textindexng3 import CatalogTextIndexNG3

from nti.contentsearch._ngrams_utils import ngrams

from nti.contentsearch.common import normalize_type_name
from nti.contentsearch.common import (	OID, NTIID, CREATOR, LAST_MODIFIED, CONTAINER_ID, COLLECTION_ID, ID)
from nti.contentsearch.common import (	ngrams_, channel_, content_, keywords_, 
										references_, recipients_, sharedWith_,  
										note_, highlight_, messageinfo_, redaction_, 
										replacementContent_, redactionExplanation_ )

import logging
logger = logging.getLogger( __name__ )

# want to make sure change the family for all catalog index fields
BaseIndex.family = BTrees.family64
CatalogIndex.family = BTrees.family64

def get_none(obj, default=None):
	return None

def get_id(obj, default=None):
	#adapted = component.getAdapter(obj, IContentResolver)
	#return adapted.get_id()
	return None

def get_channel(obj, default=None):
	#adapted = component.getAdapter(obj, IContentResolver)
	#return adapted.get_channel()
	return None

def get_containerId(obj, default=None):
	#adapted = component.getAdapter(obj, IContentResolver)
	#return adapted.get_containerId()
	return None

def get_external_oid(obj, default=None):
	#adapted = component.getAdapter(obj, IContentResolver)
	#return adapted.get_external_oid()
	return None
get_oid = get_external_oid
get_objectId = get_external_oid

def get_ntiid(obj, default=None):
	#adapted = component.getAdapter(obj, IContentResolver)
	#return adapted.get_ntiid()
	return None

def get_creator(obj, default=None):
	#adapted = component.getAdapter(obj, IContentResolver)
	#return adapted.get_creator()
	return None

def get_references(obj, default=None):
	#adapted = component.getAdapter(obj, IContentResolver)
	#return adapted.get_references()
	return None

def get_last_modified(obj, default=None):
	#adapted = component.getAdapter(obj, IContentResolver)
	#return adapted.get_last_modified()
	return None
	
def get_keywords(obj, default=None):
	#adapted = component.getAdapter(obj, IContentResolver)
	#return adapted.get_keywords()
	return None

def get_recipients(obj, default=None):
	#adapted = component.getAdapter(obj, IContentResolver)
	#return adapted.get_recipients()
	return None

def get_sharedWith(obj, default=None):
	#adapted = component.getAdapter(obj, IContentResolver)
	#return adapted.get_sharedWith()
	return None

def get_object_content(obj, default=None):
	adapted = component.getAdapter(obj, IContentResolver)
	result = adapted.get_content()
	return result.lower() if result else None

def get_note_ngrams(obj, default=None):
	return ngrams(get_object_content(obj)) if compute_ngrams else u''
		
def get_highlight_ngrams(obj, default=None):
	return ngrams(get_object_content(obj)) if compute_ngrams else u''

def get_redaction_ngrams(obj, default=None):
	return ngrams(get_object_content(obj)) if compute_ngrams else u''

def get_messageinfo_ngrams(obj, default=None):
	return ngrams(get_object_content(obj)) if compute_ngrams else u''

def get_replacement_content(obj, default=None):
	#adapted = component.getAdapter(obj, IContentResolver)
	#result = adapted.get_replacement_content()
	#return result.lower() if result else None
	return None
	
def get_redaction_explanation(obj, default=None):
	#adapted = component.getAdapter(obj, IContentResolver)
	#result = adapted.get_redaction_explanation()
	#return result.lower() if result else None
	return None
	
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
	catalog[content_] = _create_text_index(content_, get_object_content)
	return catalog
	
def create_highlight_catalog():
	catalog = _create_treadable_mixin_catalog()
	catalog[ngrams_] = _create_text_index(ngrams_, get_highlight_ngrams)
	catalog[content_] = _create_text_index(content_, get_object_content)
	return catalog

def create_redaction_catalog():
	catalog = _create_treadable_mixin_catalog()
	catalog[ngrams_] = _create_text_index(ngrams_, get_redaction_ngrams)
	catalog[content_] = _create_text_index(content_, get_object_content)
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
	catalog[content_] = _create_text_index(content_, get_object_content)
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

