import transaction

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

class DataStore():
	
	transaction_manager = transaction.TransactionManager()
	
	def __init__(self, database, users_key='users', docMap_key='docMap'):
		self.db = database
		self.users_key = users_key
		self.docMap_key = docMap_key
		assert isinstance(database, DB), 'must specify a valid DB object'
		
		self.conn = self.db.open(self.transaction_manager)
			
		with self.dbTrans() as conn:
			dbroot = conn.root()
			if not dbroot.has_key(users_key):
				dbroot[users_key] = OOBTree()
			
			if not dbroot.has_key(docMap_key):
				dbroot[docMap_key] = DocumentMap()
				
	def dbTrans(self):
		return self.transaction_manager
	
	@property	
	def root(self):
		return self.conn.root()
	
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
		self.conn.close()
		self.db.close()
