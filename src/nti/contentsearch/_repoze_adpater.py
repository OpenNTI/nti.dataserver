# -*- coding: utf-8 -*-
"""
Repoze user search adapter.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from BTrees.LFBTree import LFBucket

from zope import component
from zope import interface
from zope.annotation import factory as an_factory

from perfmetrics import metricmethod

from nti.dataserver import interfaces as nti_interfaces

from nti.contentprocessing import rank_words

from .common import is_all_query
from .common import get_type_name
from .common import sort_search_types
from ._search_query import QueryObject
from ._repoze_query import parse_query

from .common import normalize_type_name
from ._repoze_index import create_catalog
from . import interfaces as search_interfaces
from .textindexng3 import CatalogTextIndexNG3
from ._search_highlights import WORD_HIGHLIGHT
from ._search_results import empty_search_results
from ._search_results import empty_suggest_results
from ._search_indexmanager import _SearchEntityIndexManager
from ._search_results import empty_suggest_and_search_results
from .common import (content_, ngrams_, title_, tags_, post_)

@component.adapter(nti_interfaces.IEntity)
@interface.implementer( search_interfaces.IRepozeEntityIndexManager)
class _RepozeEntityIndexManager(_SearchEntityIndexManager):

	def add_catalog(self, catalog, type_name):
		if type_name not in self:
			self[type_name] = catalog
			return True
		return False

	def get_catalog(self, type_name):
		catalog = self.get(type_name, None)
		return catalog

	def remove_catalog(self, type_name):
		c = self.pop(type_name, None)
		return True if c else False

	def get_catalog_names(self):
		names = list(self.keys())
		return names

	def get_catalogs(self):
		values = list(self.values())
		return values

	def get_docids(self):
		result = set()
		for catalog in self.get_catalogs():
			fld = list(catalog.values())[0] # get first field as pivot
			result.update(fld.docids()) # use CatalogField.docids()
		return result

	def get_create_catalog(self, data, type_name=None, create=True):
		type_name = normalize_type_name(type_name or get_type_name(data))
		catalog = self.get_catalog(type_name)
		if not catalog and create:
			catalog = create_catalog(type_name)
			if catalog:
				self.add_catalog(catalog, type_name)
		return catalog

	def _adapt_searchOn_types(self, searchOn=None):
		catnames = self.get_catalog_names()
		result = [normalize_type_name(x) for x in searchOn if normalize_type_name(x) in catnames] if searchOn else catnames
		result = sort_search_types(result)
		return result

	def _get_search_fields(self, queryobject, type_name):
		if queryobject.is_phrase_search or queryobject.is_prefix_search:
			result = (content_,) if type_name != post_ else (content_, title_,)
		else:
			result = (ngrams_,) if type_name != post_ else (ngrams_, title_, tags_)
		return result
	
	@metricmethod
	def _get_hits_from_docids(self, results, doc_weights, type_name):
		# get all objects from the ds
		for docid, score in doc_weights.items():
			obj = self.get_object(docid)
			results.add((obj, score))
		
	@metricmethod
	def _do_catalog_query(self, catalog, qo, type_name, search_fields=()):
		search_fields = search_fields or self._get_search_fields(qo, type_name)
		is_all_query, queryobject = parse_query(catalog, search_fields, qo)
		if is_all_query:
			result = LFBucket()
		else:
			result = queryobject._apply(catalog, names=None)
		return result

	def _do_search(self, qo, searchOn=(), highlight_type=WORD_HIGHLIGHT, creator_method=None, search_fields=()):
		creator_method = creator_method or empty_search_results
		results = creator_method(qo)
		results.highlight_type = highlight_type
		if qo.is_empty: return results

		for type_name in searchOn:
			catalog = self.get_catalog(type_name)
			doc_weights = self._do_catalog_query(catalog, qo, type_name, search_fields=search_fields)
			self._get_hits_from_docids(results, doc_weights, type_name)

		return results

	@metricmethod
	def search(self, query, *args, **kwargs):
		qo = QueryObject.create(query, **kwargs)
		searchOn = self._adapt_searchOn_types(qo.searchOn)
		highlight_type = None if is_all_query(qo.term) else WORD_HIGHLIGHT
		results = self._do_search(qo, searchOn, highlight_type)
		return results

	def suggest(self, query, *args, **kwargs):
		qo = QueryObject.create(query, **kwargs)
		searchOn = self._adapt_searchOn_types(qo.searchOn)
		results = empty_suggest_results(qo)
		if qo.is_empty: return results

		threshold = qo.threshold
		prefix = qo.prefix or len(qo.term)
		for type_name in searchOn:
			catalog = self.get_catalog(type_name)
			textfield = catalog.get(content_, None)

			# make sure the field supports suggest
			if isinstance(textfield, CatalogTextIndexNG3):
				words_t = textfield.suggest(term=qo.term, threshold=threshold, prefix=prefix)
				results.add(map(lambda t: t[0], words_t))

		return results

	def suggest_and_search(self, query, limit=None, *args, **kwargs):
		queryobject = QueryObject.create(query, **kwargs)
		searchOn = self._adapt_searchOn_types(queryobject.searchOn)
		if ' ' in queryobject.term or queryobject.is_prefix_search or queryobject.is_phrase_search:
			results = self._do_search(queryobject,
									  searchOn,
									  creator_method=empty_suggest_and_search_results)
		else:
			result = self.suggest(queryobject, searchOn=searchOn)
			suggestions = result.suggestions
			if suggestions:
				suggestions = rank_words(query.term, suggestions)
				queryobject.term = suggestions[0]

			results = self._do_search(queryobject,
									  searchOn,
									  creator_method=empty_suggest_and_search_results,
									  search_fields=(content_,))
			results.add_suggestions(suggestions)

		return results
		
	# ----------------

	def index_content(self, data, type_name=None):
		docid = self.get_uid(data)
		catalog = self.get_create_catalog(data, type_name)
		if catalog:
			catalog.index_doc(docid, data)
			return True
		return False

	def update_content(self, data, type_name=None):
		docid = self.get_uid(data)
		catalog = self.get_create_catalog(data, type_name)
		if catalog:
			catalog.reindex_doc(docid, data)
			return True
		return False

	def delete_content(self, data, type_name=None):
		docid = self.get_uid(data)
		catalog = self.get_create_catalog(data, type_name, create=False)
		if catalog:
			catalog.unindex_doc(docid)
			return True
		return False

	def unindex_doc(self, docid):
		for catalog in self.values():
			catalog.unindex_doc(docid)
		
	def remove_index(self, type_name):
		result = self.remove_catalog(type_name)
		return result

_RepozeEntityIndexManagerFactory = an_factory(_RepozeEntityIndexManager)
