from __future__ import print_function, unicode_literals

import time

from zope import component
from zope import interface
from zope.annotation import factory as an_factory
from zope.interface.common.mapping import IFullMapping

from ZODB import loglevels

from persistent.mapping import PersistentMapping

from nti.dataserver import interfaces as nti_interfaces

from nti.contentsearch import interfaces as search_interfaces
from nti.contentsearch._search_indexmanager import _SearchEntityIndexManager

from nti.contentsearch import QueryObject
from nti.contentsearch import SearchCallWrapper
from nti.contentsearch.common import is_all_query
from nti.contentsearch.common import get_type_name
from nti.contentsearch._repoze_query import parse_query
from nti.contentsearch.common import normalize_type_name
from nti.contentsearch.common import (content_, ngrams_)
from nti.contentsearch._repoze_index import create_catalog
from nti.contentsearch.textindexng3 import CatalogTextIndexNG3
from nti.contentsearch._search_results import empty_search_results
from nti.contentsearch._search_results import empty_suggest_results
from nti.contentsearch._search_results import empty_suggest_and_search_results
from nti.contentsearch._search_highlights import (WORD_HIGHLIGHT, NGRAM_HIGHLIGHT)

import logging
logger = logging.getLogger( __name__ )

@component.adapter(nti_interfaces.IEntity)
class _RepozeEntityIndexManager(PersistentMapping, _SearchEntityIndexManager):
	interface.implements(search_interfaces.IRepozeEntityIndexManager, IFullMapping)
	
	def __init__(self):
		PersistentMapping.__init__(self)

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
	
	# ----------------
	
	def _adapt_search_on_types(self, search_on=None):
		catnames = self.get_catalog_names()
		if search_on:
			search_on = [normalize_type_name(x) for x in search_on if normalize_type_name(x) in catnames]
		return search_on or catnames

	def _get_hits_from_docids(self, results, docids, type_name):
		t = time.time()
		try:
			# get all objects from the ds
			objects = map(self.get_object, docids)
			t = time.time() - t
			results.add(objects)
		finally:
			logger.log(loglevels.BLATHER, "Getting %s %s(s) from dataserver took %s(s)" , len(docids), type_name, t)
		
	def _do_catalog_query(self, catalog, fieldname, qo, type_name):
		is_all_query, queryobject = parse_query(catalog, fieldname, qo)
		if is_all_query:
			return 0, []
		else:
			t = time.time()
			try:
				result = catalog.query(queryobject)
				t = time.time() - t
			finally:
				logger.log(loglevels.BLATHER, "Index search for %s(s) took %s(s). %s doc(s) retreived" , type_name, t, result[0])
			return result

	def _do_search(self, fieldname, qo, search_on=(), highlight_type=WORD_HIGHLIGHT, creator_method=None):
		creator_method = creator_method or empty_search_results
		results = creator_method(qo)
		results.highlight_type = highlight_type
		if qo.is_empty: return results

		for type_name in search_on:
			catalog = self.get_catalog(type_name)
			_, docids = self._do_catalog_query(catalog, fieldname, qo, type_name)
			self._get_hits_from_docids(results, docids, type_name)
			
		return results

	@SearchCallWrapper
	def search(self, query, *args, **kwargs):
		qo = QueryObject.create(query, **kwargs)
		search_on = self._adapt_search_on_types(qo.search_on)
		highlight_type = None if is_all_query(qo.term) else WORD_HIGHLIGHT
		results = self._do_search(content_, qo, search_on, highlight_type)
		return results

	def ngram_search(self, query, *args, **kwargs):
		qo = QueryObject.create(query, **kwargs)
		search_on = self._adapt_search_on_types(qo.search_on)
		highlight_type = None if is_all_query(qo.term) else NGRAM_HIGHLIGHT
		results = self._do_search(ngrams_, qo, search_on, highlight_type)
		return results

	def suggest(self, query, *args, **kwargs):
		qo = QueryObject.create(query, **kwargs)
		search_on = self._adapt_search_on_types(qo.search_on)
		results = empty_suggest_results(qo)
		if qo.is_empty: return results

		threshold = qo.threshold
		prefix = qo.prefix or len(qo.term)
		for type_name in search_on:
			catalog = self.get_catalog(type_name)
			textfield = catalog.get(content_, None)
			
			# make sure the field supports suggest
			if isinstance(textfield, CatalogTextIndexNG3):
				words_t = textfield.suggest(term=qo.term, threshold=threshold, prefix=prefix)
				results.add(map(lambda t: t[0], words_t))
	
		return results

	def suggest_and_search(self, query, limit=None, *args, **kwargs):
		queryobject = QueryObject.create(query, **kwargs)
		search_on = self._adapt_search_on_types(queryobject.search_on)
		if ' ' in query.term:
			results = self._do_search(content_, 
									  queryobject, 
									  search_on, 
									  creator_method=empty_suggest_and_search_results)
		else:
			result = self.suggest(queryobject, search_on=search_on)
			suggestions = result.suggestions
			if suggestions:
				#TODO: pick a good suggestion
				queryobject.term = list(suggestions)[0]
			
			results = self._do_search(content_,
									  queryobject,
									  search_on, 
									  creator_method=empty_suggest_and_search_results)
			results.add_suggestions(suggestions)
			
		return results

	# ----------------
		
	def index_content(self, data, type_name=None, **kwargs):
		if not data: return None
		docid = self.get_uid(data)
		catalog = self.get_create_catalog(data, type_name)
		if catalog:
			catalog.index_doc(docid, data)
		return docid

	def update_content(self, data, type_name=None, *args, **kwargs):
		if not data: return None
		docid = self.get_uid(data)
		catalog = self.get_create_catalog(data, type_name)
		if catalog:
			catalog.reindex_doc(docid, data)
		return docid

	def delete_content(self, data, type_name=None, *args, **kwargs):
		if not data: return None
		docid = self.get_uid(data)
		catalog = self.get_create_catalog(data, type_name, create=False)
		if catalog: 
			catalog.unindex_doc(docid)
		return docid

	def remove_index(self, type_name):
		result = self.remove_catalog(type_name)
		return result
		
	get_stored_indices = get_catalog_names
			
	def has_stored_indices(self):
		return len(self.get_catalog_names()) > 0
	
def _RepozeEntityIndexManagerFactory(user):
	result = an_factory(_RepozeEntityIndexManager)(user)
	return result
