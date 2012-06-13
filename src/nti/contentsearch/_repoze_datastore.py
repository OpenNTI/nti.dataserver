from __future__ import print_function, unicode_literals

from zope import interface

from BTrees.OOBTree import OOBTree
from persistent import Persistent
from persistent.mapping import PersistentMapping

from nti.contentsearch._document import DocumentMap
from nti.contentsearch.interfaces import IRepozeDataStore

import logging
logger = logging.getLogger( __name__ )

class _RepozeDataStore(PersistentMapping):
	"""
	deprecated repoze data store
	"""
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
	
class PersistentRepozeDataStore(Persistent):
	interface.implements(IRepozeDataStore)
	
	def __init__(self):
		super(PersistentRepozeDataStore, self).__init__()
		self.users = OOBTree()
		self.docmaps = OOBTree()

	def has_user(self, username):
		return username in self.users
	
	def remove_user(self, username):
		if username in self.users:
			self.users.pop(username, None)
		if username in self.docmaps:
			self.docmaps.pop(username, None)
			
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
			c = catalog_map.pop(type_name, None)
			return True if c else False
		return False

	def get_catalog_names(self, username):
		pm = self.users.get(username, {})
		names = list(pm.keys())
		return names

	def get_catalogs(self, username):
		pm = self.users.get(username, {})
		values = list(pm.values())
		return values
	
	def add_metadata(self, username, docid, meta):
		docMap = self.docmaps.get(username, None)
		if docMap and meta:
			docMap.add_metadata(docid, meta)
			return True
		return False
	
	def get_metadata(self, username, docid):
		docMap = self.docmaps.get(username, None)
		if docMap:
			try:
				result = docMap.get_metadata(docid)
				return result
			except:
				pass
		return None
	
	def remove_metadata(self, username, docid, *keys):
		docMap = self.docmaps.get(username, None)
		if docMap:
			try:
				docMap.remove_metadata(docid, *keys)
				return True
			except:
				pass
		return False
	
	def add_address(self, username, address, meta=None):
		docMap = self.docmaps.get(username, None)
		if docMap:
			docid = docMap.add(address)
			if meta:
				docMap.add_metadata(docid, meta)
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
	
	def get_or_create_docid_for_address(self, username, address, meta=None):
		docid = self.docid_for_address(username, address) or self.add_address(username, address, meta)
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
		

class RepozeDataStore(_RepozeDataStore,PersistentRepozeDataStore):
	pass

