import warnings

from ZODB import DB
from BTrees.OOBTree import OOBTree
from persistent.mapping import PersistentMapping
from repoze.catalog.document import DocumentMap

import contextlib

class RepozeDataStore(object):

	def __init__(self, database, users_key='users', docMap_key='docMap'):
		self.db = database
		self.users_key = users_key or 'users'
		self.docMap_key = docMap_key or 'docMap'
		assert isinstance(database, DB), 'must specify a valid DB object'

		with self.db.transaction() as conn:
			# FIXME: Do this with a generations schema installer
			dbroot = conn.root()
			if not dbroot.has_key(users_key):
				dbroot[users_key] = OOBTree()

			if not dbroot.has_key(docMap_key):
				dbroot[docMap_key] = DocumentMap()
		# FIXME: This entire object should probably be in the database.
		# Then all these problems go away.

	@contextlib.contextmanager
	def dbTrans(self):
		warnings.warn( "This method is going away!", FutureWarning, stacklevel=3 )
		# FIXME: This is not thread safe. It's not even gevent safe!
		# FIXME: This should go away entirely. It clearly doesn't
		# do what it seems to do, as the connection is tied
		# to the global transaction and not actually committed when
		# this context does anything
		conn = self.db.open()
		self.conn = conn
		try:
			yield conn
		finally:
			# FIXME: We cannot even close this connection, it's
			# joined to the global transaction
			del self.conn

	@property
	def root(self):
		# FIXME: Not thread/gevent safe
		return self.conn.root()

	@property
	def users(self):
		# FIXME: Not thread/gevent safe
		return self.root[self.users_key]

	@property
	def docMap(self):
		# FIXME: Not thread/gevent safe
		return self.root[self.docMap_key]

	def add_catalog(self, username, catalog, type_name):
		# FIXME: Not thread/gevent safe
		if username not in self.users:
			self.users[username] = PersistentMapping()
		if type_name not in self.users[username]:
			self.users[username][type_name] = catalog

	def get_catalog(self, username, type_name):
		# FIXME: Not thread/gevent safe
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
		# FIXME: We should never do this in code
		self.db.pack()

	def close(self):
		self.db.close()

	def __del__(self):
		try:
			self.close()
		except:
			pass
