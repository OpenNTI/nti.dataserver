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

from . import interfaces as search_interfaces
from .textindexng3 import CatalogTextIndexNG3
from . import _discriminators as discriminators

# repoze discriminator functions. Some of them are simply aliases for legacy purposes
get_ntiid = discriminators.get_ntiid
get_channel = discriminators.get_channel
get_creator = discriminators.get_creator
get_keywords = discriminators.get_keywords
get_post_tags = discriminators.get_post_tags
get_ngrams = discriminators.get_object_ngrams
get_content = discriminators.get_object_content
get_title = discriminators.get_title_and_ngrams
get_containerId = discriminators.get_containerId
get_last_modified = discriminators.get_last_modified
get_object_ngrams = discriminators.get_object_ngrams
get_object_content = discriminators.get_object_content
get_post_title = discriminators.get_post_title_and_ngrams
get_content_and_ngrams = discriminators.get_content_and_ngrams
get_replacementContent = discriminators.get_replacement_content_and_ngrams
get_redactionExplanation = discriminators.get_redaction_explanation_and_ngrams
# alias for bwc
get_replacement_content = get_replacementContent
get_redaction_explanation = get_redactionExplanation

def _flatten_list(result, default=None):
	result = ' '.join(result) if result else default
	return result

def get_sharedWith(obj, default=None):
	result = discriminators.get_sharedWith(obj)
	return _flatten_list(result, default)

def get_references(obj, default=None):
	result = discriminators.get_references(obj)
	return _flatten_list(result, default)

def get_recipients(obj, default=None):
	result = discriminators.get_recipients(obj)
	return _flatten_list(result, default)

def create_catalog(type_name):
	creator = component.queryUtility(search_interfaces.IRepozeCatalogCreator, name=type_name)
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
			func(catalog, name, iface)

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

def _named_field_creator(catalog, name, iface):
	discriminator = _get_discriminator(name)
	catalog[name] = CatalogFieldIndex(discriminator)

def _keyword_field_creator(catalog, name, iface):
	discriminator = _get_discriminator(name)
	catalog[name] = CatalogKeywordIndex(discriminator)

def _title_field_creator(catalog, name, iface):
	catalog[name] = CatalogTextIndexNG3(name, get_title)
_post_title_field_creator = _title_field_creator

def _post_tags_field_creator(catalog, name, iface):
	discriminator = get_post_tags
	catalog[name] = CatalogKeywordIndex(discriminator)
