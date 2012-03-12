from zope import component
from zope import interface

from repoze.catalog.query import Contains

from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver._Dataserver import get_object_by_oid

from nti.contentsearch import interfaces
from nti.contentsearch.common import empty_search_result
from nti.contentsearch._repoze_index import get_index_hit
from nti.contentsearch._repoze_datastore import DataStore

import logging
logger = logging.getLogger( __name__ )


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

	def _get_server_objects(self, docMap, docIds):
		result = []
		with self.dataserver.dbTrans() as conn:
			for docId in docIds:
				try:
					oid = docMap.address_for_docid(docId)
					_obj = get_object_by_oid(conn, oid)
					result.append(_obj)
				except:
					pass
		return result
	
	def _get_catalog_names(self):
		with self.datastore.dbTrans():
			return self.get_catalog_names(self.username)
			
	def _adapt_search_on_types(self, search_on=None):
		if search_on:
			lm = lambda x: x[0:-1] if x.endswith('s') else x
			search_on = [lm(x).lower() for x in search_on]
		return search_on

	def search(self, query, limit=None, search_on=None, *args, **kwargs):
		search_on = self._adapt_search_on_types(search_on)
		search_on = search_on if search_on else self._get_catalog_names()
		
		results = empty_search_result()
		items = results['Items']
		with self.store.dbTrans():
			docMap = self.store.docMap
			for type_name in search_on:
				catalog = self.datastore.get_catalog(self.username, type_name)
				if not catalog: continue
				_, docIds = catalog.query(Contains('content', query))
				server_objects = self._get_server_objects(docMap, docIds) 
				for so in server_objects:
					hit = get_index_hit(so)
					if hit: items.append(hit)
				
		return results	