from brownie.caching import LFUCache

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

