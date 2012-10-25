from __future__ import print_function, unicode_literals

from zope import component
from zope import interface
from zope.annotation import factory as an_factory
from zope.interface.common.mapping import IFullMapping

from perfmetrics import metricmethod

from nti.dataserver import interfaces as nti_interfaces

from nti.contentsearch.common import is_all_query
from nti.contentsearch.common import get_type_name
from nti.contentsearch.common import sort_search_types
from nti.contentsearch.common import (content_, ngrams_)
from nti.contentsearch._search_query import QueryObject
from nti.contentsearch._repoze_query import parse_query
from nti.contentsearch._content_utils import rank_words
from nti.contentsearch.common import normalize_type_name
from nti.contentsearch._repoze_index import create_catalog
from nti.contentsearch import interfaces as search_interfaces
from nti.contentsearch.textindexng3 import CatalogTextIndexNG3
from nti.contentsearch._search_highlights import WORD_HIGHLIGHT
from nti.contentsearch._search_results import empty_search_results
from nti.contentsearch._search_results import empty_suggest_results
from nti.contentsearch._search_indexmanager import _SearchEntityIndexManager
from nti.contentsearch._search_results import empty_suggest_and_search_results

import logging
logger = logging.getLogger( __name__ )

@component.adapter(nti_interfaces.IEntity)
@interface.implementer( search_interfaces.IRepozeEntityIndexManager, IFullMapping )
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

	def _adapt_searchon_types(self, searchon=None):
		catnames = self.get_catalog_names()
		if searchon:
			searchon = [normalize_type_name(x) for x in searchon if normalize_type_name(x) in catnames]
		result = searchon or catnames
		result = sort_search_types(result)
		return result

	def _get_search_field(self, queryobject):
		fieldname = content_ if queryobject.is_phrase_search or queryobject.is_prefix_search else ngrams_
		return fieldname
	
	@metricmethod
	def _get_hits_from_docids(self, results, doc_weights, type_name):
		# get all objects from the ds
		for docid, score in doc_weights.items():
			obj = self.get_object(docid)
			results.add((obj, score))
		
	@metricmethod
	def _do_catalog_query(self, catalog, qo, type_name, fieldname=None):
		fieldname = fieldname or self._get_search_field(qo)
		is_all_query, queryobject = parse_query(catalog, fieldname, qo)
		if is_all_query:
			result =  {}
		else:
			result = queryobject._apply(catalog, names=None)
		return result

	def _do_search(self, qo, searchon=(), highlight_type=WORD_HIGHLIGHT, creator_method=None, fieldname=None):
		creator_method = creator_method or empty_search_results
		results = creator_method(qo)
		results.highlight_type = highlight_type
		if qo.is_empty: return results

		for type_name in searchon:
			catalog = self.get_catalog(type_name)
			doc_weights = self._do_catalog_query(catalog, qo, type_name, fieldname=fieldname)
			self._get_hits_from_docids(results, doc_weights, type_name)

		return results

	@metricmethod
	def search(self, query, *args, **kwargs):
		qo = QueryObject.create(query, **kwargs)
		searchon = self._adapt_searchon_types(qo.searchon)
		highlight_type = None if is_all_query(qo.term) else WORD_HIGHLIGHT
		results = self._do_search(qo, searchon, highlight_type)
		return results

	def suggest(self, query, *args, **kwargs):
		qo = QueryObject.create(query, **kwargs)
		searchon = self._adapt_searchon_types(qo.searchon)
		results = empty_suggest_results(qo)
		if qo.is_empty: return results

		threshold = qo.threshold
		prefix = qo.prefix or len(qo.term)
		for type_name in searchon:
			catalog = self.get_catalog(type_name)
			textfield = catalog.get(content_, None)

			# make sure the field supports suggest
			if isinstance(textfield, CatalogTextIndexNG3):
				words_t = textfield.suggest(term=qo.term, threshold=threshold, prefix=prefix)
				results.add(map(lambda t: t[0], words_t))

		return results

	def suggest_and_search(self, query, limit=None, *args, **kwargs):
		queryobject = QueryObject.create(query, **kwargs)
		searchon = self._adapt_searchon_types(queryobject.searchon)
		if ' ' in queryobject.term or queryobject.is_prefix_search or queryobject.is_phrase_search:
			results = self._do_search(queryobject,
									  searchon,
									  creator_method=empty_suggest_and_search_results)
		else:
			result = self.suggest(queryobject, searchon=searchon)
			suggestions = result.suggestions
			if suggestions:
				suggestions = rank_words(query.term, suggestions)
				queryobject.term = suggestions[0]

			results = self._do_search(queryobject,
									  searchon,
									  creator_method=empty_suggest_and_search_results,
									  fieldname=content_)
			results.add_suggestions(suggestions)

		return results
		
	# ----------------

	def index_content(self, data, type_name=None, **kwargs):
		if not data: return None
		docid = self.get_uid(data)
		catalog = self.get_create_catalog(data, type_name)
		if catalog:
			catalog.index_doc(docid, data)
			return True
		return False

	def update_content(self, data, type_name=None, *args, **kwargs):
		if not data: return None
		docid = self.get_uid(data)
		catalog = self.get_create_catalog(data, type_name)
		if catalog:
			catalog.reindex_doc(docid, data)
			return True
		return False

	def delete_content(self, data, type_name=None, *args, **kwargs):
		if not data: return None
		docid = self.get_uid(data)
		catalog = self.get_create_catalog(data, type_name, create=False)
		if catalog:
			catalog.unindex_doc(docid)
			return True
		return False

	def remove_index(self, type_name):
		result = self.remove_catalog(type_name)
		return result

	get_stored_indices = get_catalog_names

	def has_stored_indices(self):
		return len(self.get_catalog_names()) > 0

def _RepozeEntityIndexManagerFactory(user):
	result = an_factory(_RepozeEntityIndexManager)(user)
	return result
