from __future__ import print_function, unicode_literals

import BTrees

from zope import interface
from zope import component
from zope.index.text.baseindex import BaseIndex

from repoze.catalog.catalog import Catalog
from repoze.catalog.indexes.common import CatalogIndex
from repoze.catalog.indexes.text import CatalogTextIndex
from repoze.catalog.indexes.field import CatalogFieldIndex
from repoze.catalog.indexes.keyword import CatalogKeywordIndex


from nti.contentsearch import compute_ngrams
from nti.contentsearch import interfaces as search_interfaces
from nti.contentsearch.textindexng3 import CatalogTextIndexNG3

from nti.contentsearch._ngrams_utils import ngrams

from nti.contentsearch.common import normalize_type_name
from nti.contentsearch.common import (	note_, highlight_, messageinfo_, redaction_, content_ )
# from nti.contentsearch.common import (	OID, NTIID, CREATOR, LAST_MODIFIED, CONTAINER_ID, COLLECTION_ID, ID)
#from nti.contentsearch.common import (	note_, highlight_, messageinfo_, redaction_ )
#										references_, recipients_, sharedWith_,  
#										note_, highlight_, messageinfo_, redaction_, 
#										replacementContent_, redactionExplanation_ )

import logging
logger = logging.getLogger( __name__ )

# want to make sure change the family for all catalog index fields
BaseIndex.family = BTrees.family64
CatalogIndex.family = BTrees.family64

def get_id(obj, default):
	adapted = component.getAdapter(obj, search_interfaces.IContentResolver)
	return adapted.get_id() or default

def get_channel(obj, default):
	adapted = component.getAdapter(obj, search_interfaces.IContentResolver)
	return adapted.get_channel() or default

def get_containerId(obj, default):
	adapted = component.getAdapter(obj, search_interfaces.IContentResolver)
	return adapted.get_containerId() or default

def get_external_oid(obj, default):
	adapted = component.getAdapter(obj, search_interfaces.IContentResolver)
	return adapted.get_external_oid() or default
get_oid = get_external_oid
get_objectId = get_external_oid

def get_ntiid(obj, default):
	adapted = component.getAdapter(obj, search_interfaces.IContentResolver)
	return adapted.get_ntiid() or default

def get_creator(obj, default):
	adapted = component.getAdapter(obj, search_interfaces.IContentResolver)
	return adapted.get_creator() or default

def get_references(obj, default):
	adapted = component.getAdapter(obj, search_interfaces.IContentResolver)
	return adapted.get_references() or default

def get_last_modified(obj, default):
	adapted = component.getAdapter(obj, search_interfaces.IContentResolver)
	return adapted.get_last_modified() or default
	
def get_keywords(obj, default):
	adapted = component.getAdapter(obj, search_interfaces.IContentResolver)
	return adapted.get_keywords() or default

def get_recipients(obj, default):
	adapted = component.getAdapter(obj, search_interfaces.IContentResolver)
	result = adapted.get_recipients()
	result = ' '.join(result) if result else default
	return result

def get_sharedWith(obj, default):
	adapted = component.getAdapter(obj, search_interfaces.IContentResolver)
	result = adapted.get_sharedWith()
	result = ' '.join(result) if result else default
	return result

def get_object_content(obj, default=None):
	adapted = component.getAdapter(obj, search_interfaces.IContentResolver)
	result = adapted.get_content()
	return result.lower() if result else None
get_content = get_object_content

def get_object_ngrams(obj, default=None):
	return ngrams(get_object_content(obj), default)
get_ngrams = get_object_ngrams

def get_note_ngrams(obj, default=None):
	return ngrams(get_object_content(obj)) if compute_ngrams else u''
		
def get_highlight_ngrams(obj, default=None):
	return ngrams(get_object_content(obj)) if compute_ngrams else u''

def get_redaction_ngrams(obj, default=None):
	return ngrams(get_object_content(obj)) if compute_ngrams else u''

def get_messageinfo_ngrams(obj, default=None):
	return ngrams(get_object_content(obj)) if compute_ngrams else u''

def get_replacement_content(obj, default=None):
	adapted = component.getAdapter(obj, search_interfaces.IContentResolver)
	result = adapted.get_replacement_content()
	return result.lower() if result else None
	
def get_redaction_explanation(obj, default=None):
	adapted = component.getAdapter(obj, search_interfaces.IContentResolver)
	result = adapted.get_redaction_explanation()
	return result.lower() if result else None
	
def _create_text_index(field, discriminator):
	return CatalogTextIndexNG3(field, discriminator)

def _create_treadable_mixin_catalog():
	catalog = Catalog(family=BTrees.family64)
	#catalog[NTIID] = CatalogFieldIndex(get_ntiid)
	#catalog[OID] = CatalogFieldIndex(get_external_oid)
	#catalog[CREATOR] = CatalogFieldIndex(get_creator)
	#catalog[keywords_] = CatalogKeywordIndex(get_keywords)
	#catalog[sharedWith_] = CatalogKeywordIndex(get_sharedWith)
	#catalog[CONTAINER_ID] = CatalogFieldIndex(get_containerId)
	#catalog[LAST_MODIFIED] = CatalogFieldIndex(get_last_modified)
	return catalog

def create_notes_catalog():
	catalog = _create_treadable_mixin_catalog()
	#catalog[references_] = CatalogKeywordIndex(get_references)
	#catalog[ngrams_] = _create_text_index(ngrams_, get_note_ngrams)
	catalog[content_] = _create_text_index(content_, get_object_content)
	return catalog
	
def create_highlight_catalog():
	catalog = _create_treadable_mixin_catalog()
	#catalog[ngrams_] = _create_text_index(ngrams_, get_highlight_ngrams)
	catalog[content_] = _create_text_index(content_, get_object_content)
	return catalog

def create_redaction_catalog():
	catalog = _create_treadable_mixin_catalog()
	#catalog[ngrams_] = _create_text_index(ngrams_, get_redaction_ngrams)
	catalog[content_] = _create_text_index(content_, get_object_content)
	#catalog[replacementContent_] = _create_text_index(replacementContent_, get_replacement_content)
	#catalog[redactionExplanation_] = _create_text_index(redactionExplanation_, get_redaction_explanation)
	return catalog

def create_messageinfo_catalog():
	catalog = _create_treadable_mixin_catalog()
	#catalog[ID] = CatalogFieldIndex(get_id)
	#catalog[channel_] = CatalogFieldIndex(get_channel)
	#catalog[recipients_] = CatalogKeywordIndex(get_recipients)
	#catalog[references_] = CatalogKeywordIndex(get_references)
	#catalog[ngrams_] = _create_text_index(ngrams_, get_messageinfo_ngrams)
	catalog[content_] = _create_text_index(content_, get_object_content)
	return catalog

def create_catalog(type_name):
	creator = component.queryUtility(search_interfaces.IRepozeCatalogCreator,  name=type_name)
	return creator.create() if creator else None

# catalog creators

@interface.implementer(search_interfaces.IRepozeCatalogCreator)
class _RepozeCatalogCreator(object):
	def create(self):
		catalog = Catalog()
		for name, func in component.getUtilitiesFor( self._iface ):
			func( catalog, name,  self._iface  )		
		return catalog
		
class _RepozeNoteCatalogCreator(_RepozeCatalogCreator):
	_iface = search_interfaces.INoteRepozeCatalogCreator

class _RepozeHighlightCatalogCreator(_RepozeCatalogCreator):
	_iface = search_interfaces.IHighlightRepozeCatalogCreator

class _RepozeRedactionCatalogCreator(_RepozeCatalogCreator):
	_iface = search_interfaces.IRedactionRepozeCatalogCreator

class _RepozeMessageInfoCatalogCreator(_RepozeCatalogCreator):
	_iface = search_interfaces.IMessageInfoRepozeCatalogCreator

# repoze index field creators

def _get_discriminator(name):
	result = globals().get("get_%s" % name, None)
	if not result or not callable(result):
		result = name
	return result

def _zopytext_field_creator(catalog, name, iface):
	discriminator = _get_discriminator(name)
	catalog[name] = CatalogTextIndexNG3(name, discriminator)
	
def _text_field_creator(catalog, name, iface):
	discriminator = _get_discriminator(name)
	catalog[name] = CatalogTextIndex(discriminator)
	
def _named_field_creator(catalog, name, iface ):
	discriminator = _get_discriminator(name)
	catalog[name] = CatalogFieldIndex( discriminator )

def _keyword_field_creator(catalog, name, iface ):
	discriminator = _get_discriminator(name)
	catalog[name] = CatalogKeywordIndex( discriminator )

def _ngrams_field_creator(catalog, name, iface):
	catalog[name] = CatalogTextIndexNG3(name, get_ngrams)

