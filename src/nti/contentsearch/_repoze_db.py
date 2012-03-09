import transaction
from gevent.local import local

from ZODB import DB
from BTrees.OOBTree import OOBTree
from persistent.mapping import PersistentMapping
from repoze.catalog.document import DocumentMap

# =====================

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
	
# =====================

class _ContextManager(object):
	"""
	Context manager for db connections
	"""
	
	local = local()
	
	def __init__(self, db):
		self.db = db
		self.tm = None
		self.conn = None
		self.txn = None

	def __enter__(self):
		self.tm = transaction.TransactionManager()
		self.conn = self.db.open( self.tm )
		self.txn = self.tm.begin()
		self.local.cm = self
		return self.conn
		
	def __exit__(self, t, v, tb):
		try:
			if t is None:
				self.tm.commit()
			else:
				self.tm.abort()
			self.tm = None
		finally:
			self.close()
	
	def close(self):
		if self.conn:
			try:
				self.conn.close()
			except: 
				pass
			
		self.tm = None
		self.conn = None
			
		try:
			del self.local.cm
		except:
			pass
		
	def connected(self):
		return self.conn is not None
	
	def abort(self):
		if self.tm:
			self.tm.abort()
			
	def commit(self):
		if self.tm:
			self.tm.commit()
		
	@classmethod
	def get(cls):
		return cls.local.cm

# =====================

class DataStore():
	def __init__(self, database, users_key='users', docMap_key='docMap'):
		self.db = database
		self.users_key = users_key
		self.docMap_key = docMap_key
		assert isinstance(database, DB), 'must specify a valid DB object'
		
		with self.dbTrans() as conn:
			dbroot = conn.root()
			if not dbroot.has_key(users_key):
				dbroot[users_key] = OOBTree()
			
			if not dbroot.has_key(docMap_key):
				dbroot[docMap_key] = DocumentMap()
				
		
	def dbTrans(self):
		return _ContextManager(self.db)
	
	@property	
	def root(self):
		return _ContextManager.get().conn.root()
	
	@property	
	def users(self):
		return self.root[self.users_key]
	
	@property	
	def docMap(self):
		return self.root[self.docMap_key]
		
	def add_catalog(self, user, catalog, type_name):
		if user not in self.users:
			self.users[user] = PersistentMapping()
		if type_name not in self.users[user]:
			self.users[user][type_name] = catalog
	
	def get_catalog(self, user, type_name):
		catalog = None
		pm = self.users.get(user, None)
		if pm:
			catalog = pm.get(type_name, None)
		return catalog
		
	def pack(self):
		self.db.pack()
		
	def close(self):
		self.db.close()
