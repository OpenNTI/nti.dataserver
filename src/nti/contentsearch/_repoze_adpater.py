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

from .constants import content_
from ._search_query import QueryObject
from ._repoze_query import parse_query
from ._repoze_index import create_catalog
from . import interfaces as search_interfaces
from .constants import ugd_indexable_type_names
from ._search_results import empty_search_results
from ._search_results import empty_suggest_results
from ._search_indexmanager import _SearchEntityIndexManager
from ._search_results import empty_suggest_and_search_results
from . import zopyxtxng3_interfaces as zopyx_search_interfaces
from .common import (get_type_name, sort_search_types, normalize_type_name)

@component.adapter(nti_interfaces.IEntity)
@interface.implementer(search_interfaces.IRepozeEntityIndexManager)
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
			fld = list(catalog.values())[0]  # get first field as pivot
			result.update(fld.docids())  # use CatalogField.docids()
		return result

	def get_create_catalog(self, data, type_name=None, create=True):
		type_name = normalize_type_name(type_name or get_type_name(data))
		catalog = self.get_catalog(type_name)
		if not catalog and create:
			catalog = create_catalog(type_name)
			if catalog:
				self.add_catalog(catalog, type_name)
		return catalog

	def _valid_type(self, type_name, catnames):
		return type_name in catnames and type_name in ugd_indexable_type_names

	def _adapt_search_on_types(self, searchOn=()):
		cns = self.get_catalog_names()
		result = [normalize_type_name(x) for x in searchOn if self._valid_type(x, cns)] if searchOn else cns
		result = sort_search_types(result)
		return result

	@metricmethod
	def _get_hits_from_docids(self, results, doc_weights, type_name):
		# get all objects from the ds
		for docid, score in doc_weights.items():
			obj = self.get_object(docid)
			results.add((obj, score))

	@metricmethod
	def _do_catalog_query(self, catalog, qo, type_name):
		is_all_query, queryobject = parse_query(qo, type_name)
		if is_all_query:
			result = LFBucket()
		else:
			result = queryobject._apply(catalog, names=None)
		return result

	def _do_search(self, qo, searchOn=(), creator_method=None):
		creator_method = creator_method or empty_search_results
		results = creator_method(qo)
		if qo.is_empty: return results

		for type_name in searchOn:
			catalog = self.get_catalog(type_name)
			doc_weights = self._do_catalog_query(catalog, qo, type_name)
			self._get_hits_from_docids(results, doc_weights, type_name)

		return results

	@metricmethod
	def search(self, query, *args, **kwargs):
		qo = QueryObject.create(query, **kwargs)
		searchOn = self._adapt_search_on_types(qo.searchOn)
		results = self._do_search(qo, searchOn)
		return results

	def suggest(self, query, *args, **kwargs):
		qo = QueryObject.create(query, **kwargs)
		searchOn = self._adapt_search_on_types(qo.searchOn)
		results = empty_suggest_results(qo)
		if qo.is_empty: return results

		threshold = qo.threshold
		prefix = qo.prefix or len(qo.term)
		for type_name in searchOn:
			catalog = self.get_catalog(type_name)
			textfield = catalog.get(content_, None)
			if zopyx_search_interfaces.ICatalogTextIndexNG3.providedBy(textfield):
				words_t = textfield.suggest(term=qo.term, threshold=threshold, prefix=prefix)
				results.add(map(lambda t: t[0], words_t))

		return results

	def suggest_and_search(self, query, limit=None, *args, **kwargs):
		queryobject = QueryObject.create(query, **kwargs)
		searchOn = self._adapt_search_on_types(queryobject.searchOn)
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
									  creator_method=empty_suggest_and_search_results)
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
