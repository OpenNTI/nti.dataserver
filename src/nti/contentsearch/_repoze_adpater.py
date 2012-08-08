from __future__ import print_function, unicode_literals

from zope import component
from zope import interface
from zope.annotation import factory as an_factory
from zope.interface.common.mapping import IFullMapping

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
from nti.contentsearch._repoze_index import create_catalog
from nti.contentsearch._search_external import get_search_hit
from nti.contentsearch.textindexng3 import CatalogTextIndexNG3
from nti.contentsearch._search_results import empty_search_result
from nti.contentsearch._search_results import empty_suggest_result
from nti.contentsearch._search_highlights import (WORD_HIGHLIGHT, NGRAM_HIGHLIGHT)
from nti.contentsearch.common import (NTIID, LAST_MODIFIED, ITEMS, HIT_COUNT, SUGGESTIONS, content_, ngrams_)

import logging
logger = logging.getLogger( __name__ )

@component.adapter(nti_interfaces.IUser)
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
			search_on = [normalize_type_name(x) for x in search_on if x in catnames]
		return search_on or catnames

	def _get_hits_from_docids(self, qo, docids, highlight_type=None):
		
		limit = qo.limit		
		if not docids:
			return [], 0
		
		# get all objects from the ds
		objects = map(self.get_object, docids)
		
		# get all index hits
		length = len(objects)
		hits = map(get_search_hit, objects, [qo.term]*length, [highlight_type]*length)
		
		# filter if required
		items = hits[:limit] if limit else hits
		
		# get last modified
		lm = reduce(lambda x,y: max(x, y.get(LAST_MODIFIED,0)), items, 0)
		
		return items, lm

	def _do_catalog_query(self, catalog, fieldname, qo):
		is_all_query, queryobject = parse_query(catalog, fieldname, qo)
		if is_all_query:
			return 0, []
		else:
			limit = qo.limit
			return catalog.query(queryobject, limit=limit)

	def _do_search(self, fieldname, qo, search_on=(), highlight_type=None):
		
		results = empty_search_result(qo.term)
		if qo.is_empty: return results

		lm = 0
		items = results[ITEMS]
		for type_name in search_on:
			catalog = self.get_catalog(type_name)
			
			# search catalog
			_, docids = self._do_catalog_query(catalog, fieldname, qo)
			hits, hits_lm = self._get_hits_from_docids(qo, docids, highlight_type)
			
			# calc the last modified date
			lm = max(lm, hits_lm)
			
			# set items
			for hit in hits:
				items[hit[NTIID]] = hit

		results[LAST_MODIFIED] = lm
		results[HIT_COUNT] = len(items)
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
	quick_search = ngram_search

	def suggest(self, query, *args, **kwargs):
		qo = QueryObject.create(query, **kwargs)
		search_on = self._adapt_search_on_types(qo.search_on)
		results = empty_suggest_result(qo.term)
		if qo.is_empty: return results

		limit = qo.limit
		suggestions = set()
		threshold = qo.threshold
		prefix = qo.prefix or len(qo.term)

		for type_name in search_on:
			catalog = self.get_catalog(type_name)
			textfield = catalog.get(content_, None)
			
			# make sure the field supports suggest
			if isinstance(textfield, CatalogTextIndexNG3):
				words_t = textfield.suggest(term=qo.term, threshold=threshold, prefix=prefix)
				for t in words_t:
					suggestions.add(t[0])
	
		suggestions = suggestions[:limit] if limit and limit > 0 else suggestions
		results[ITEMS] = list(suggestions)
		results[HIT_COUNT] = len(suggestions)
		return results

	def suggest_and_search(self, query, limit=None, *args, **kwargs):
		qo = QueryObject.create(query, **kwargs)
		search_on = self._adapt_search_on_types(qo.search_on)
		if ' ' in query.term:
			suggestions = []
			result = self.search(qo, search_on=search_on)
		else:
			result = self.suggest(qo, search_on=search_on)
			suggestions = result[ITEMS]
			if suggestions:
				qo.term = suggestions[0]
				result = self.search(qo, search_on=search_on)
			else:
				result = self.search(qo, search_on=search_on)
		result[SUGGESTIONS] = suggestions
		return result

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
