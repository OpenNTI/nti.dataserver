from zope import interface

from BTrees.OOBTree import OOBTree
from persistent.mapping import PersistentMapping
from repoze.catalog.document import DocumentMap

from nti.contentsearch.interfaces import IRepozeDataStore

class RepozeDataStore(PersistentMapping):
	interface.implements(IRepozeDataStore)
	
	def __init__(self, users_key='users', docMap_key='docMap'):
		PersistentMapping.__init__(self)
		self.users_key = users_key or 'users'
		self.docMap_key = docMap_key or 'docMap'
		
		if not self.users_key in self:
			self[self.users_key] = OOBTree()
		
		if not self.docMap_key in self:
			self[self.docMap_key] = OOBTree()
	
	@property
	def users(self):
		return self[self.users_key]
	
	@property
	def docmaps(self):
		return self[self.docMap_key]
	
	def has_user(self, username):
		return username in self.users
	
	def add_catalog(self, username, catalog, type_name):
		if username not in self.users:
			self.users[username] = OOBTree()
			self.docmaps[username] = DocumentMap()
			
		if type_name not in self.users[username]:
			self.users[username][type_name] = catalog

	def get_catalog(self, username, type_name):
		pm = self.users.get(username, {})
		catalog = pm.get(type_name, None)
		return catalog

	def remove_catalog(self, username, type_name):
		catalog_map = self.users.get(username, None)
		if catalog_map:
			catalog_map.pop(type_name, None)
			if not catalog_map:
				self.docmaps.pop(username, None)
			return True
		return False

	def get_catalog_names(self, username):
		pm = self.users.get(username, {})
		names = list(pm.keys())
		return names

	def get_catalogs(self, username):
		pm = self.users.get(username, {})
		values = list(pm.values())
		return values
	
	def add_address(self, username, address):
		docMap = self.docmaps.get(username, None)
		if docMap:
			docid = docMap.add(address)
			return docid
		else:
			return None
	
	def remove_docid(self, username, docid):
		docMap = self.docmaps.get(username, None)
		if docMap:
			result = docMap.remove_docid(docid)
			return result
		else:
			return False
	
	def get_or_create_docid_for_address(self, username, address):
		docid = self.docid_for_address(username, address) or self.add_address(username, address)
		return docid
		
	def docid_for_address(self, username, address):
		docMap = self.docmaps.get(username, None)
		if docMap:
			docid = docMap.docid_for_address(address)
			return docid
		else:
			return None
	
	def address_for_docid(self, username, docid):
		docMap = self.docmaps.get(username, None)
		if docMap:
			address = docMap.address_for_docid(docid)
			return address
		else:
			return None
		
	def get_docids(self, username):
		docMap = self.docmaps.get(username, None)
		if docMap:
			return docMap.docid_to_address.keys()
		return []
		
