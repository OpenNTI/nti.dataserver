import UserDict
from heapq import nsmallest
from operator import itemgetter

import logging
logger = logging.getLogger( __name__ )

# -----------------------------

_instances = {}
def singleton(cls):
	if cls not in _instances:
		_instances[cls] = cls()
	return _instances[cls]

class IndexTypeMixin(object):
	def __init__(self, type_instance, idx):
		self.idx = idx
		self.type_instance = type_instance

	@property
	def index(self):
		return self.idx

	@property
	def indexname(self):
		return self.idx.indexname

	@property
	def instance(self):
		return self.type_instance

	@property
	def type_name(self):
		return self.type_instance.__class__.__name__

	def __str__( self ):
		return self.indexname

	def __repr__( self ):
		return 'IndexTypeMixin(indexname=%s, type=%s)' %  (self.indexname, self.type_instance)

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

class _Counter(dict):
	def __missing__(self, key):
		return 0

class LFUMap(UserDict.DictMixin):
	
	_kwd_mark = object()  
	
	def __init__(self, maxitems, maxremoval=1, callback=None):
		self.cache = {}
		self.use_count = _Counter()  
		self.maxitems = maxitems
		self.maxremoval = min(maxremoval, maxitems)
	
	def __len__(self):
		return len(self.cache)

	def __contains__(self, key):
		return key in self.cache
	
	def __getitem__(self, key):
		item = self.cache[key]
		self.use_count[key] += 1
		return item

	def __setitem__(self, key, value):
		self.cache[key] = value
		self.use_count[key] = 0
		if len(self.cache) > self.maxitems:
			for key, _ in nsmallest(self.maxremoval, 
									self.use_count.iteritems(),
									key=itemgetter(1)):
				del self.cache[key], self.use_count[key]

	def __delitem__(self, key):
		self.cache.pop(key)
		if key in self.use_count:
			self.use_count.pop(key)
	
	def __iter__(self):
		return iter(self.cache)
			
	def iteritems(self):
		return self.cache.iteritems()

# -----------------------------

