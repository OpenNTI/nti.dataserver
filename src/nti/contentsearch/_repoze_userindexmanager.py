from zope import component
from zope import interface

from repoze.catalog.query import Contains

from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.ntiids import find_object_with_ntiid

from nti.contentsearch import interfaces
from nti.contentsearch.common import get_type_name
from nti.contentsearch.common import empty_search_result
from nti.contentsearch.common import empty_suggest_result
from nti.contentsearch._repoze_index import get_ntiid
from nti.contentsearch._repoze_index import get_index_hit
from nti.contentsearch._repoze_index import create_catalog
from nti.contentsearch._repoze_datastore import DataStore
from nti.contentsearch.textindexng3 import CatalogTextIndexNG3
from nti.contentsearch.common import (NTIID, LAST_MODIFIED, ITEMS, HIT_COUNT, SUGGESTIONS, content_, ngrams_)

import logging
logger = logging.getLogger( __name__ )

# -----------------------------

class RepozeUserIndexManager(object):
	interface.implements(interfaces.IUserIndexManager)

	def __init__(self, username, repoze_store, dataserver=None):
		self.username = username
		self.datastore = repoze_store
		self.ds = dataserver or component.queryUtility( nti_interfaces.IDataserver )
		assert self.ds, 'must specify a valid data server'
		assert isinstance(self.datastore, DataStore), 'must specify a valid repoze store'

	# -------------------
	
	def __str__( self ):
		return self.username

	def __repr__( self ):
		return 'RepozeUserIndexManager(user=%s)' % self.username

	# -------------------
	
	def get_username(self):
		return self.username
	
	@property
	def store(self):
		return self.datastore

	@property
	def dataserver(self):
		return self.ds
	
	# -------------------

	def _normalize_name(self, x):
		result = u''
		if x:
			result =x[0:-1].lower() if x.endswith('s') else x.lower()
		return unicode(result)
	
	def _get_catalog_names(self):
		with self.datastore.dbTrans():
			return self.datastore.get_catalog_names(self.username)
			
	def _adapt_search_on_types(self, search_on=None):
		if search_on:
			search_on = [self._normalize_name(x) for x in search_on]
		return search_on

	def _get_hits_from_docids(self, docMap, docIds, limit=None, query=None, use_word_highlight=True, *args, **kwargs):
		lm =  0
		items = []
		with self.dataserver.dbTrans():
			for docId in docIds:
				ntiid = docMap.address_for_docid(docId)
				try:
					svr_obj = find_object_with_ntiid(ntiid, dataserver=self.dataserver)
					if callable( getattr( svr_obj, 'toExternalObject', None ) ):
						svr_obj = svr_obj.toExternalObject()
					hit = get_index_hit(svr_obj, query=query, use_word_highlight=use_word_highlight, **kwargs)
					if hit:
						items.append(hit)
						lm = max(lm, hit[LAST_MODIFIED])
						if limit and len(items) >= limit:
							break
				except:
					logger.error("cannot find object with NTIID '%s' referenced in index" % ntiid)
		return items, lm
				
	# -------------------
	
	def _do_search(self, field, query, limit=None, use_word_highlight=True, *args, **kwargs):
		
		search_on = self._adapt_search_on_types(kwargs.get('search_on', None))
		search_on = search_on if search_on else self._get_catalog_names()
		
		lm = 0
		results = empty_search_result(query)
		items = results[ITEMS]
		with self.store.dbTrans():
			docMap = self.store.docMap
			for type_name in search_on:
				catalog = self.datastore.get_catalog(self.username, type_name)
				if catalog: 
					_, docIds = catalog.query(Contains(field, query))
					hits, hits_lm = self._get_hits_from_docids(	docMap,
																docIds,
																limit=limit,
																query=query,
																use_word_highlight=use_word_highlight,
																**kwargs)
					if hits:
						lm = max(lm, hits_lm)
						for hit in hits:
							items[hit[NTIID]] = hit
			
		results[LAST_MODIFIED] = lm
		results[HIT_COUNT] = len(items)	
		return results	
	
	def search(self, query, limit=None, *args, **kwargs):
		results = self._do_search(content_, query, limit, True, *args, **kwargs)
		return results	
	
	def ngram_search(self, query, limit=None, *args, **kwargs):
		results = self._do_search(ngrams_, query, limit, False, *args, **kwargs)
		return results	
	quick_search = ngram_search
	
	def suggest(self, term, limit=None, prefix=None, *args, **kwargs):
		
		search_on = self._adapt_search_on_types(kwargs.get('search_on', None))
		search_on = search_on if search_on else self._get_catalog_names()
		threshold = kwargs.get('threshold', 0.4999)
		prefix = prefix or len(term)
				
		suggestions = set()		
		results = empty_suggest_result(term)
		with self.store.dbTrans():
			for type_name in search_on:
				catalog = self.datastore.get_catalog(self.username, type_name)
				textfield = catalog.get(content_, None)
				if not isinstance(textfield, CatalogTextIndexNG3): continue
				words_t = textfield.suggest(term=unicode(term), threshold=threshold, prefix=prefix) 
				for t in words_t:
					suggestions.add(t[0])
		
		suggestions = suggestions[:limit] if limit and limit > 0 else suggestions
		results[ITEMS] = list(suggestions)
		results[HIT_COUNT] = len(suggestions)
		return results
	
	def suggest_and_search(self, query, limit=None, *args, **kwargs):
		if ' ' in query:
			suggestions = []
			result = self.search(query, limit, *args, **kwargs)
		else:
			result = self.suggest(query, limit=limit, *args, **kwargs)
			suggestions = result[ITEMS]
			if suggestions:
				result = self.search(query, limit, *args, **kwargs)
			else:
				result = self.search(query, limit, *args, **kwargs)

		result[SUGGESTIONS] = suggestions
		return result
	
	# -------------------
	
	def _get_create_catalog(self, data, type_name=None, create=True):
		type_name = self._normalize_name(type_name or get_type_name(data))
		catalog = self.store.get_catalog(self.username, type_name)
		if not catalog and create:
			catalog = create_catalog(type_name)
			if catalog:
				self.store.add_catalog(self.username, catalog, type_name)
		return catalog
	
	def index_content(self, data, type_name=None, **kwargs):
		docid = None
		ntiid = get_ntiid(data)
		with self.store.dbTrans():
			catalog = self._get_create_catalog(data, type_name)
			if catalog and ntiid:
				docMap = self.store.docMap
				docid = docMap.add(ntiid)
				catalog.index_doc(docid, data)
		return docid

	def update_content(self, data, type_name=None, *args, **kwargs):
		ntiid = get_ntiid(data)
		if not ntiid: return None
		with self.store.dbTrans():
			docMap = self.store.docMap
			docid = docMap.docid_for_address(ntiid)
			if docid:
				catalog = self._get_create_catalog(data, type_name)
				catalog.reindex_doc(docid, data)
			else:
				docid = self.index_content(data, type_name)
		return docid

	def delete_content(self, data, type_name=None, *args, **kwargs):
		ntiid = get_ntiid(data)
		if not ntiid: return None
		with self.store.dbTrans():
			docMap = self.store.docMap
			docid = docMap.docid_for_address(ntiid)
			if docid:
				catalog = self._get_create_catalog(data, type_name)
				catalog.unindex_doc(docid)
		return docid
		
	def remove_index(self, type_name):
		with self.store.dbTrans():
			result = self.store.remove_catalog(self.username, type_name)
			return result
	
	# -------------------
	
	def docid_for_address(self, address):
		with self.store.dbTrans():
			docMap = self.store.docMap
			docid = docMap.docid_for_address(address)
			return docid
	
# -----------------------------

def ruim_factory(repoze_store=None, dataserver=None):
	def f(username, *args, **kwargs):
		_ds = kwargs['dataserver'] if 'dataserver' in kwargs else dataserver
		_store = repoze_store or kwargs.get('repoze_store', None) or kwargs.get('store', None)
		return RepozeUserIndexManager(username, _store, _ds)
	return f
