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

from nti.contentsearch import interfaces as search_interfaces
from nti.contentsearch.textindexng3 import CatalogTextIndexNG3

from nti.contentsearch._ngrams_utils import ngrams

import logging
logger = logging.getLogger( __name__ )

# want to make sure change the family for all catalog index fields
BaseIndex.family = BTrees.family64
CatalogIndex.family = BTrees.family64

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

def get_last_modified(obj, default):
	adapted = component.getAdapter(obj, search_interfaces.IContentResolver)
	result = adapted.get_last_modified()
	return result or default
	
def get_keywords(obj, default):
	adapted = component.getAdapter(obj, search_interfaces.IContentResolver)
	return adapted.get_keywords() or default

def _flatten_list(result, default):
	result = ' '.join(result) if result else default
	return result

def get_references(obj, default):
	adapted = component.getAdapter(obj, search_interfaces.IContentResolver)
	result = adapted.get_references()
	return _flatten_list(result, default)

def get_recipients(obj, default):
	adapted = component.getAdapter(obj, search_interfaces.IContentResolver)
	result = adapted.get_recipients()
	return _flatten_list(result, default)

def get_sharedWith(obj, default):
	adapted = component.getAdapter(obj, search_interfaces.IContentResolver)
	result = adapted.get_sharedWith()
	return _flatten_list(result, default)

def get_object_content(obj, default=None):
	adapted = component.getAdapter(obj, search_interfaces.IContentResolver)
	result = adapted.get_content()
	return result.lower() if result else None
get_content = get_object_content

def get_object_ngrams(obj, default=None):
	return ngrams(get_object_content(obj)) or default
get_ngrams = get_object_ngrams

def get_replacement_content(obj, default=None):
	adapted = component.getAdapter(obj, search_interfaces.IContentResolver)
	result = adapted.get_replacement_content()
	return result.lower() if result else None
get_replacementContent = get_replacement_content

def get_redaction_explanation(obj, default=None):
	adapted = component.getAdapter(obj, search_interfaces.IContentResolver)
	result = adapted.get_redaction_explanation()
	return result.lower() if result else None
get_redactionExplanation = get_redaction_explanation

def create_catalog(type_name):
	creator = component.queryUtility(search_interfaces.IRepozeCatalogCreator,  name=type_name)
	return creator.create() if creator else None

# catalog creators

@interface.implementer(search_interfaces.IRepozeCatalogCreator)
class _RepozeCatalogCreator(object):
	def create(self):
		catalog = Catalog()
		self._set4(catalog, search_interfaces.IRepozeCatalogFieldCreator)
		self._set4(catalog, self._iface)
		return catalog

	def _set4(self, catalog, iface):
		for name, func in component.getUtilitiesFor(iface):
			func( catalog, name, iface)		
	
class _RepozeNoteCatalogCreator(_RepozeCatalogCreator):
	_iface = search_interfaces.INoteRepozeCatalogFieldCreator

class _RepozeHighlightCatalogCreator(_RepozeCatalogCreator):
	_iface = search_interfaces.IHighlightRepozeCatalogFieldCreator

class _RepozeRedactionCatalogCreator(_RepozeCatalogCreator):
	_iface = search_interfaces.IRedactionRepozeCatalogFieldCreator

class _RepozeMessageInfoCatalogCreator(_RepozeCatalogCreator):
	_iface = search_interfaces.IMessageInfoRepozeCatalogFieldCreator

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
	
@interface.implementer(search_interfaces.ISearchFeatures)
class _DefaultRepozeSearchFeatures(object):
	is_ngram_search_supported = False
	is_word_suggest_supported = False
	
@interface.implementer(search_interfaces.ISearchFeatures)
class _NgramRepozeSearchFeatures(object):
	is_ngram_search_supported = True
	is_word_suggest_supported = False
	
@interface.implementer(search_interfaces.ISearchFeatures)
class _FullRepozeSearchFeatures(object):
	is_ngram_search_supported = True
	is_word_suggest_supported = True

