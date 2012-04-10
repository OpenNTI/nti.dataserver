import six
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
	
	__int_properties__ 	= ('limit', 'maxdist', 'prefix', 'surround', 'maxchars')
	__properties__ 		= ('term', 'query', 'books', 'indexname') + __int_properties__

	def __init__(self, *args, **kwargs):
		term = kwargs.get('term', None) or kwargs.get('query', None)
		assert term is not None, 'must specify a query term'
		self._data = {}
		for k, v in kwargs.items():
			if k and v is not None:
				self.__setitem__(k, v)
				
	def keys(self):
		return self._data.keys()
	
	def __str__( self ):
		return self.term

	def __repr__( self ):
		return 'QueryObject(%s)' % self._data
	
	def __getitem__(self, key):
		if key.lower() in self.__properties__:
			key = key.lower()
		return self._data[key]
			
	def __setitem__(self, key, val):
		if key.lower() in self.__properties__:
			key = key.lower()
			if key in ('query', 'term'):
				self.set_term(val)
			elif key in self.__int_properties__:
				self._data[key] = int(val) if val is not None else val
			else:
				self._data[key] = unicode(val) if isinstance(val, six.string_types) else val
		else:
			self._data[key] = unicode(val) if isinstance(val, six.string_types) else val
		
	# -- search -- 
	
	@property
	def books(self):
		books = self._data.get('books', [])
		if not books:
			indexname = self._data.get('indexname', None)
			if indexname:
				books = [indexname]	
		return books
	
	@property
	def username(self):
		return self._data.get('username', None)
	
	def get_term(self):
		return self._data['term']

	def set_term(self, term):
		self._data['term'] = unicode(term) if term is not None else term
	
	term = property(get_term, set_term)
	query = term
		
	def get_limit(self):
		return self._data.get('limit', None)
	
	def set_limit(self, limit=None):
		self.__setitem__('limit', limit)
	
	limit = property(get_limit, set_limit)
	
	def get_subqueries(self):
		result = []
		for k in self.keys(): 
			if k not in self.__properties__:
				result.append( (k, self._data.get(k)) )
		return result
	
	# -- suggest -- 
	
	def get_maxdist(self):
		return self._data.get('maxdist', None)

	def set_maxdist(self, maxdist):
		self.__setitem__('maxdist', maxdist)
		
	maxdist = property(get_maxdist, set_maxdist)
	
	def get_prefix(self):
		return self._data.get('prefix', None)

	def set_prefix(self, prefix):
		self.__setitem__('prefix', prefix)
		
	prefix = property(get_prefix, set_prefix)
	
	# -- highlight -- 
	
	def get_surround(self):
		return self._data.get('surround', 20)

	def set_surround(self, surround=20):
		self.__setitem__('surround', surround)
		
	surround = property(get_surround, set_surround)
	
	def get_maxchars(self):
		return self._data.get('maxchars', 300)
	
	def set_maxchars(self, maxchars=300):
		self.__setitem__('maxchars', maxchars)
		
	maxchars = property(get_maxchars, set_maxchars)
	
	# ---------------
	
	@classmethod
	def parse_query_properties(cls, **kwargs):
		result = {}
		for k, v in kwargs.items(): 
			if k.lower() in cls.__properties__:
				result[k] = v
		return result
	
	@classmethod
	def create(cls, query, **kwargs):
		if isinstance(query, six.string_types):
			queryobject = QueryObject(term=query)
		else:
			assert isinstance(query, QueryObject) 
			queryobject = query
			
		for k, v in kwargs.items():
			if k and v is not None:
				queryobject[k] = v
				
		return queryobject
	
# -----------------------------

def create_repoze_datastore(users_key='users', docMap_key='docMap'):
	return RepozeDataStore(users_key=users_key, docMap_key=docMap_key)
