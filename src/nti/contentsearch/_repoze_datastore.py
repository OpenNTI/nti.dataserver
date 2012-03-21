import transaction

from ZODB import DB
from BTrees.OOBTree import OOBTree
from persistent.mapping import PersistentMapping
from repoze.catalog.document import DocumentMap

# -----------------------------------

class RepozeDataStore():
	
	transaction_manager = transaction.manager
	
	def __init__(self, database, users_key='users', docMap_key='docMap'):
		self.db = database
		self.users_key = users_key or 'users'
		self.docMap_key = docMap_key or 'docMap'
		assert isinstance(database, DB), 'must specify a valid DB object'
		
		self.conn = self.db.open(self.transaction_manager)
			
		with self.dbTrans():
			dbroot = self.root
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
		
	def add_catalog(self, username, catalog, type_name):
		if username not in self.users:
			self.users[username] = PersistentMapping()
		if type_name not in self.users[username]:
			self.users[username][type_name] = catalog
	
	def get_catalog(self, username, type_name):
		pm = self.users.get(username, {})
		catalog = pm.get(type_name, None)
		return catalog
		
	def remove_catalog(self, username, type_name):
		pm = self.users.get(username, None)
		if pm and type_name in pm:
			pm.pop(type_name)
			return True
		return False
		
	def get_catalog_names(self, username):
		pm = self.users.get(username, {})
		names = pm.keys()
		return names
	
	def get_catalogs(self, username):
		pm = self.users.get(username, {})
		values = pm.values()
		return values
	
	def pack(self):
		self.db.pack()
		
	def close(self):
		self.conn.close()
		self.db.close()
		
	def __del__(self):
		try:
			self.close()
		except:
			pass
