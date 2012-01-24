import logging
logger = logging.getLogger( __name__ )


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

