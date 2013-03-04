# -*- coding: utf-8 -*-
"""
Repoze index definitions and discriminators.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import BTrees

from zope import interface
from zope import component

from repoze.catalog.catalog import Catalog
from repoze.catalog.indexes.text import CatalogTextIndex
from repoze.catalog.indexes.field import CatalogFieldIndex
from repoze.catalog.indexes.keyword import CatalogKeywordIndex

from nti.contentprocessing import compute_ngrams

from . import interfaces as search_interfaces
from .textindexng3 import CatalogTextIndexNG3

def get_containerId(obj, default=None):
	adapted = component.getAdapter(obj, search_interfaces.IContainerIDResolver)
	return adapted.get_containerId() or default

def get_ntiid(obj, default=None):
	adapted = component.getAdapter(obj, search_interfaces.INTIIDResolver)
	return adapted.get_ntiid() or default

def get_creator(obj, default=None):
	adapted = component.getAdapter(obj, search_interfaces.ICreatorResolver)
	return adapted.get_creator() or default

def get_last_modified(obj, default=None):
	adapted = component.getAdapter(obj, search_interfaces.ILastModifiedResolver)
	result = adapted.get_last_modified()
	return result or default
	
def get_keywords(obj, default=()):
	adapted = component.queryAdapter(obj, search_interfaces.IThreadableContentResolver)
	result = adapted.get_keywords() if adapted else None
	result = [x.lower() for x in result] if result else None
	return result or default

def _flatten_list(result, default=None):
	result = ' '.join(result) if result else default
	return result

def get_sharedWith(obj, default=None):
	adapted = component.queryAdapter(obj, search_interfaces.IShareableContentResolver)
	result = adapted.get_sharedWith() if adapted else None
	return _flatten_list(result, default)

def get_references(obj, default=None):
	adapted = component.queryAdapter(obj, search_interfaces.INoteContentResolver)
	result = adapted.get_references() if adapted else None
	return _flatten_list(result, default)

def get_channel(obj, default=None):
	adapted = component.getAdapter(obj, search_interfaces.IMessageInfoContentResolver)
	return adapted.get_channel() or default

def get_recipients(obj, default=None):
	adapted = component.getAdapter(obj, search_interfaces.IMessageInfoContentResolver)
	result = adapted.get_recipients()
	return _flatten_list(result, default)

def get_replacement_content(obj, default=None):
	adapted = component.getAdapter(obj, search_interfaces.IRedactionContentResolver)
	result = adapted.get_replacement_content()
	return result.lower() if result else None
get_replacementContent = get_replacement_content

def get_redaction_explanation(obj, default=None):
	adapted = component.getAdapter(obj, search_interfaces.IRedactionContentResolver)
	result = adapted.get_redaction_explanation()
	return result.lower() if result else None
get_redactionExplanation = get_redaction_explanation

def get_post_title(obj, default=None):
	adapted = component.getAdapter(obj, search_interfaces.IPostContentResolver)
	result = adapted.get_title()
	return result.lower() if result else None

def get_post_tags(obj, default=()):
	adapted = component.queryAdapter(obj, search_interfaces.IPostContentResolver)
	result = adapted.get_tags() if adapted else None
	result = [x.lower() for x in result] if result else None
	return result or default

def get_object_content(obj, default=None):
	adapted = component.getAdapter(obj, search_interfaces.IContentResolver)
	result = adapted.get_content()
	return result.lower() if result else None
get_content = get_object_content

def get_object_ngrams(obj, default=None):
	content = get_object_content(obj, default)
	n_grams = compute_ngrams(content) if content else default
	return n_grams if n_grams else default
get_ngrams = get_object_ngrams

def get_content_and_ngrams(obj, default=None):
	content = get_object_content(obj)
	n_grams = compute_ngrams(content)
	result = '%s %s' % (content, n_grams) if content else u''
	return result or default

def create_catalog(type_name):
	creator = component.queryUtility(search_interfaces.IRepozeCatalogCreator,  name=type_name)
	return creator.create() if creator else None

# catalog creators

@interface.implementer(search_interfaces.IRepozeCatalogCreator)
class _RepozeCatalogCreator(object):
	def create(self):
		catalog = Catalog(family=BTrees.family64)
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

class _RepozePostCatalogCreator(_RepozeCatalogCreator):
	_iface = search_interfaces.IPostRepozeCatalogFieldCreator
	
# repoze index field creators

def _get_discriminator(name):
	result = globals().get("get_%s" % name, None)
	if not result or not callable(result):
		result = name
	return result

def _content_ngrams_field_creator(catalog, name, iface):
	catalog[name] = CatalogTextIndexNG3(name, get_content_and_ngrams)
	
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
	
@interface.implementer(search_interfaces.ISearchFeatures)
class _DefaultRepozeSearchFeatures(object):
	is_ngram_search_supported = True
	is_word_suggest_supported = False
	
@interface.implementer(search_interfaces.ISearchFeatures)
class _FullRepozeSearchFeatures(object):
	is_ngram_search_supported = True
	is_word_suggest_supported = True
