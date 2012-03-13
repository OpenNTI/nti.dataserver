from numbers import Integral

from zope import component
from zope import interface

from repoze.catalog.query import Contains

from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver._Dataserver import get_object_by_oid

from nti.contentsearch import interfaces
from nti.contentsearch.common import empty_search_result
from nti.contentsearch.common import empty_suggest_result
from nti.contentsearch._repoze_index import get_objectId
from nti.contentsearch._repoze_index import get_type_name
from nti.contentsearch._repoze_index import get_index_hit
from nti.contentsearch._repoze_index import create_catalog
from nti.contentsearch._repoze_datastore import DataStore
from nti.contentsearch.textindexng3 import CatalogTextIndexNG3
from nti.contentsearch.common import  (CONTENT, LAST_MODIFIED, ITEMS, HIT_COUNT, SUGGESTIONS)

import logging
logger = logging.getLogger( __name__ )

# -----------------------------

class RepozeUserIndexManager(object):
	interface.implements(interfaces.IUserIndexManager)

	def __init__(self, username, repoze_store, dataserver=None):
		self.username = username
		self.datastore = repoze_store
		self.ds = dataserver or component.queryUtility( nti_interfaces.IDataserver )
		assert isinstance(repoze_store, DataStore), 'must specify a valid repoze store'
		assert isinstance(dataserver, 'must specify a valid data server')

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

	def _get_hits_from_docids(self, docMap, docIds, limit=None, items=None):
		lm =  0
		items = items if items else []
		with self.dataserver.dbTrans() as conn:
			for docId in docIds:
				try:
					oid = docMap.address_for_docid(docId)
					so = get_object_by_oid(conn, oid)
					hit = get_index_hit(so)
					if hit:
						items.append(hit)
						lm = max(lm, hit[LAST_MODIFIED])
						if limit and len(items) >= limit:
							break
				except:
					pass
		return items, lm
				
	def _get_catalog_names(self):
		with self.datastore.dbTrans():
			return self.get_catalog_names(self.username)
			
	def _adapt_search_on_types(self, search_on=None):
		if search_on:
			lm = lambda x: x[0:-1] if x.endswith('s') else x
			search_on = [lm(x).lower() for x in search_on]
		return search_on

	# -------------------
	
	def search(self, query, limit=None, search_on=None, *args, **kwargs):
		search_on = self._adapt_search_on_types(search_on)
		search_on = search_on if search_on else self._get_catalog_names()
		
		lm = 0
		count = 0
		hits = {}
		results = empty_search_result(query)
		with self.store.dbTrans():
			docMap = self.store.docMap
			for type_name in search_on:
				catalog = self.datastore.get_catalog(self.username, type_name)
				if catalog: 
					_, docIds = catalog.query(Contains(CONTENT, query))
					hits_items, hits_lm = self._get_hits_from_docids(docMap, docIds, limit=limit)
					if hits_items:
						lm = max(lm, hits_lm)
						hits[type_name] = hits_items
						count = count + len(hits_items)
			
		items = results[ITEMS]
		for v in hits.values():
			if limit:
				ridx = int( limit * (len(v)/count) )
				items.extend(v[:ridx])
			else:
				items.extend(v)
				
		results[HIT_COUNT] = count	
		results[LAST_MODIFIED] = lm
		return results	
	
	def quick_search(self, query, limit=None, search_on=None):
		return empty_search_result(query)
	
	def suggest(self, term, limit=None, prefix=None, search_on=None, *args, **kwargs):
		search_on = self._adapt_search_on_types(search_on)
		search_on = search_on if search_on else self._get_catalog_names()
		prefix = -1 if not isinstance(prefix, Integral) else prefix
		threshold = kwargs.get('threshold', 0.75)
		
		suggestions = set()		
		results = empty_suggest_result(term)
		with self.store.dbTrans():
			for type_name in search_on:
				catalog = self.datastore.get_catalog(self.username, type_name)
				if not isinstance(catalog, CatalogTextIndexNG3): continue
				words = catalog.suggest(term=term, threshold=threshold, prefix=prefix) 
				suggestions.update(words)
		
		suggestions = suggestions[:limit] if limit and limit > 0 else suggestions
		results[SUGGESTIONS] = suggestions
		return results
	
	def suggest_and_search(self, query, limit=None, search_on=None, *args, **kwargs):
		if ' ' in query:
			suggestions = []
			result = self.search(query, limit, search_on, *args, **kwargs)
		else:
			result = self.suggest(query, limit=limit, search_on=search_on, **kwargs)
			suggestions = result[SUGGESTIONS]
			if len(suggestions)>0:
				result = self.search(query, limit, search_on, *args, **kwargs)
			else:
				result = self.search(query, limit, search_on, *args, **kwargs)

		result[SUGGESTIONS] = suggestions
		return result
	
	# -------------------
	
	def _get_create_catalog(self, data, type_name=None, create=True):
		type_name = type_name or get_type_name(data)
		catalog = self.store.get_catalog(self.username, type_name)
		if not catalog and create:
			catalog = create_catalog(type_name)
			if catalog:
				self.store.add_catalog(self.username, catalog, type_name)
		return catalog
	
	def index_content(self, data, type_name=None):
		docid = None
		oid = get_objectId(data)
		with self.store.dbTrans():
			catalog = self._get_create_catalog(data, type_name)
			if catalog and oid:
				docMap = self.store.docMap
				docid = docMap.add(oid)
				catalog.index_doc(docid, data)
		return docid

	def update_content(self, data, type_name=None):
		oid = get_objectId(data)
		if not oid: return None
		with self.store.dbTrans():
			docMap = self.store.docMap
			docid = docMap.docid_for_address(oid)
			if docid:
				catalog = self._get_create_catalog(data, type_name)
				catalog.reindex_doc(docid, data)
			else:
				docid = self.index_content(data, type_name)
		return docid

	def delete_content(self, data, type_name=None):
		oid = get_objectId(data)
		if not oid: return None
		with self.store.dbTrans():
			docMap = self.store.docMap
			docid = docMap.docid_for_address(oid)
			if docid:
				catalog = self.store.get_catalog(self.username, type_name)
				catalog.unindex_doc(docid)
		return docid
		
	def remove_index(self, type_name):
		with self.store.dbTrans():
			result = self.store.remove_catalog(self.username, type_name)
			return result
	