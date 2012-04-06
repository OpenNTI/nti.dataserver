import UserDict
from brownie.caching import LFUCache

import logging
logger = logging.getLogger( __name__ )

from nti.contentsearch._repoze_datastore import RepozeDataStore

# -----------------------------

class NoOpCM(object):

	singleton = None
	
	def __new__(cls, *args, **kwargs):
		if not cls.singleton:
			cls.singleton = super(NoOpCM, cls).__new__(cls, *args, **kwargs)
		return cls.singleton
	
	def __enter__(self,*args):
		return self

	def __exit__(self,*args):
		pass
	
# -----------------------------

class LFUMap(LFUCache):

	def __init__(self, maxsize, on_removal_callback=None):
		super(LFUMap, self).__init__(maxsize=maxsize)
		self.on_removal_callback = on_removal_callback
		
	def __delitem__(self, key):
		if self.on_removal_callback:
			value = dict.__getitem__(self, key)
		super(LFUMap, self).__delitem__(key)
		if self.on_removal_callback:
			self.on_removal_callback(key, value)
	
# -----------------------------

class QueryObject(object, UserDict.DictMixin):
	
	def __init__(self, *args, **kwargs):
		term = kwargs.get('term', None) or kwargs.get('query', None)
		assert term, 'must specify a query term'
		self._data = dict(kwargs)
		self._data['term'] = unicode(term)
		
	@property
	def books(self):
		indexname = self._data.get('indexname', None)
		if indexname:
			return [indexname]
		else:
			books = self._data.get('books', None) or  ['prealgebra']
			return books
	
	@property
	def term(self):
		return self._data['term']
	query=term

	@property
	def username(self):
		return self._data.get('username', None)
	
	@property
	def limit(self):
		return self._data.get('limit', None)
	
	def keys(self):
		return self._data.keys()
	
	def __str__( self ):
		return self.term

	def __repr__( self ):
		return 'QueryObject(%s)' % self._data

# -----------------------------

def create_repoze_datastore(users_key='users', docMap_key='docMap'):
	return RepozeDataStore(users_key=users_key, docMap_key=docMap_key)
