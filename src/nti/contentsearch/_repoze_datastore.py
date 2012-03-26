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
			self[self.docMap_key] = DocumentMap()
	
	@property
	def users(self):
		return self[self.users_key]

	@property
	def docMap(self):
		return self[self.docMap_key]

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
		names = list(pm.keys())
		return names

	def get_catalogs(self, username):
		pm = self.users.get(username, {})
		values = list(pm.values())
		return values
	
	def add_address(self, address):
		docid = self.docMap.add(address)
		return docid
	
	def remove_docid(self, docid):
		result = self.docMap.remove_docid(docid)
		return result
	
	def docid_for_address(self, address):
		docid = self.docMap.docid_for_address(address)
		return docid
	
	def address_for_docid(self, docid):
		address = self.docMap.address_for_docid(docid)
		return address
