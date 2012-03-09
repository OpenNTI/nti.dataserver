import logging
logger = logging.getLogger( __name__ )

#import time
#from hashlib import md5


#from contenttypes import empty_suggest_result
#from contenttypes import merge_search_results
#from contenttypes import merge_suggest_results
#from contenttypes import empty_suggest_and_search_result
#from contenttypes import merge_suggest_and_search_results

from zope import component
from zope import interface

from nti.dataserver import interfaces as nti_interfaces

from nti.contentsearch import interfaces
from nti.contentsearch._repoze_datastore import DataStore
#from nti.contentsearch.contenttypes import empty_search_result

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

	def _get_catalog_names(self):
		with self.datastore.dbTrans():
			return self.get_catalog_names(self.username)
			
	def _adapt_search_on_types(self, search_on=None):
		if search_on:
			lm = lambda x: x[0:-1] if x.endswith('s') else x
			search_on = [lm(x).lower() for x in search_on]
		return search_on

	def search(self, query, limit=None, search_on=None):
		search_on = self._adapt_search_on_types(search_on)
		search_on = search_on if search_on else self._get_catalog_names()
		#result = None
		with self.store.dbTrans():
			for _ in search_on:
				pass #catalog = self.datastore.get_catalog(self.username, type_name)
				
