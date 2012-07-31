from __future__ import print_function, unicode_literals

import contextlib

import zope.intid
from zope import component
from zope import interface

from nti.dataserver import interfaces as nti_interfaces

from nti.contentsearch import interfaces
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
from nti.contentsearch.interfaces import IUserIndexManagerFactory
from nti.contentsearch.common import (WORD_HIGHLIGHT, NGRAM_HIGHLIGHT)
from nti.contentsearch.common import (NTIID, LAST_MODIFIED, ITEMS, HIT_COUNT, SUGGESTIONS, content_, ngrams_)

import logging
logger = logging.getLogger( __name__ )

@contextlib.contextmanager
def repoze_context_manager():
	yield component.getUtility( interfaces.IRepozeDataStore )
	
def get_stored_indices(username):
	with repoze_context_manager():
		store = component.getUtility( interfaces.IRepozeDataStore )
		return store.get_catalog_names(username)
			
def has_stored_indices(username):
	names = get_stored_indices(username)
	return True if names else False

class RepozeUserIndexManager(object):
	interface.implements(interfaces.IUserIndexManager)

	def __init__(self, username):
		self.username = username

	def __str__( self ):
		return self.username

	def __repr__( self ):
		return 'RepozeUserIndexManager(user=%s)' % self.username

	def get_username(self):
		return self.username
	
	@property
	def store(self):
		return component.getUtility( interfaces.IRepozeDataStore )
	datastore = store
	
	def get_uid(self, obj):
		_ds_intid = component.getUtility( zope.intid.IIntIds )
		return _ds_intid.getId(obj)
	
	def get_object(self, uid):
		_ds_intid = component.getUtility( zope.intid.IIntIds )
		return _ds_intid.getObject(uid)
		
	@property
	def dataserver(self):
		return component.getUtility( nti_interfaces.IDataserver )

	def _adapt_search_on_types(self, search_on=None):
		if search_on:
			search_on = [normalize_type_name(x) for x in search_on]
		return search_on or self.store.get_catalog_names(self.username)

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
		with repoze_context_manager():
			for type_name in search_on:
				catalog = self.datastore.get_catalog(self.username, type_name)
				if catalog:
					_, docids = self._do_catalog_query(catalog, fieldname, qo)
					hits, hits_lm = self._get_hits_from_docids(qo, docids, highlight_type)
					lm = max(lm, hits_lm)
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

		with repoze_context_manager():
			for type_name in search_on:
				catalog = self.datastore.get_catalog(self.username, type_name)
				textfield = catalog.get(content_, None)
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

	def _get_create_catalog(self, data, type_name=None, create=True):
		type_name = normalize_type_name(type_name or get_type_name(data))
		catalog = self.store.get_catalog(self.username, type_name)
		if not catalog and create:
			catalog = create_catalog(type_name)
			if catalog:
				self.store.add_catalog(self.username, catalog, type_name)
		return catalog
	
	def index_content(self, data, type_name=None, **kwargs):
		if not data: return None
		docid = self.get_uid(data)
		with repoze_context_manager():
			catalog = self._get_create_catalog(data, type_name)
			if catalog:
				catalog.index_doc(docid, data)
		return docid

	def update_content(self, data, type_name=None, *args, **kwargs):
		if not data: return None
		docid = self.get_uid(data)
		with repoze_context_manager():
			catalog = self._get_create_catalog(data, type_name)
			if catalog:
				catalog.reindex_doc(docid, data)
		return docid

	def delete_content(self, data, type_name=None, *args, **kwargs):
		if not data: return None
		docid = self.get_uid(data)
		with repoze_context_manager():
			catalog = self._get_create_catalog(data, type_name, create=False)
			if catalog: 
				catalog.unindex_doc(docid)
		return docid

	def remove_index(self, type_name):
		with repoze_context_manager():
			result = self.store.remove_catalog(self.username, type_name)
			return result
		
	def get_stored_indices(self):
		names = get_stored_indices(self.username)
		return names
	get_catalog_names = get_stored_indices
			
	def has_stored_indices(self):
		result = has_stored_indices(self.username)
		return result
	
class RepozeUserIndexManagerFactory(object):
	interface.implements(IUserIndexManagerFactory)

	singleton = None

	def __new__(cls, *args, **kwargs):
		if not cls.singleton:
			cls.singleton = super(RepozeUserIndexManagerFactory, cls).__new__(cls, *args, **kwargs)
		return cls.singleton

	def __str__( self ):
		with repoze_context_manager():
			return 'users=%s' % len(self.store.users)

	def __repr__( self ):
		with repoze_context_manager():
			return 'ReoozeUserIndexManagerFactory(users=%s)' % len(self.store.users)
	
	@property
	def store(self):
		return component.getUtility( interfaces.IRepozeDataStore )
		
	@property
	def dataserver(self):
		return component.queryUtility( nti_interfaces.IDataserver )
	
	def __call__(self, username, *args, **kwargs):
		create = kwargs.get('create', False)
		if create or has_stored_indices(username):
			uim = RepozeUserIndexManager(username)
			return uim
		else:
			return None
	
	def on_item_removed(self, key, value):
		try:
			value.close()
		except:
			logger.exception("Error while closing index manager %s" % key)
			
def ruim_factory(*args, **kwargs):
	return RepozeUserIndexManagerFactory()
