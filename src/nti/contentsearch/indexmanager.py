import logging
logger = logging.getLogger( __name__ )

import os
import gevent

from whoosh import index

from _indexagent import IndexAgent

import contenttypes
from contenttypes import empty_search_result
from contenttypes import empty_suggest_result
from contenttypes import merge_search_results
from contenttypes import merge_suggest_results
from contenttypes import empty_suggest_and_search_result
from contenttypes import merge_suggest_and_search_results
from indexstorage import create_directory_index_storage
from indexstorage import create_zodb_index_storage

from zope import interface
from . import interfaces
from bookindexmanager import BookIndexManager
from userindexmanager import UserIndexManager
from contenttypes import content_type_class
from contenttypes import IndexableContentMetaclass

class IndexManager(object):
	"""
	Provides a basic index manager
	"""
	interface.implements(interfaces.IIndexManager)
	indexmanager = None

	@classmethod
	def get_shared_indexmanager(cls):
		return cls.indexmanager

	##############################

	def __new__(cls, *args, **kwargs):
		if not cls.indexmanager:
			cls.indexmanager = super(IndexManager, cls).__new__(cls, *args, **kwargs)
		return cls.indexmanager

	def __init__(self, storage=None, use_md5=True, user_index_dir="/tmp", dataserver=None):
		self.books = {}
		self.users = {}
		self.use_md5 = use_md5
		self.dataserver = dataserver
		self._indexagent = IndexAgent( self )
		self.storage = storage or create_directory_index_storage(user_index_dir)

	def dbTrans(self):
		return self.storage.dbTrans()

	@classmethod
	def dsTrans( cls ):
		return cls.get_shared_indexmanager().dbTrans()

	##############################

	def add_book(self, indexdir="/tmp/", indexname="prealgebra"):
		result = False
		if not self.books.has_key(indexname) and \
			   index.exists_in(indexdir, indexname=indexname):

			self.books[indexname] = BookIndexManager(indexdir, indexname)
			result = True

		return result

	def get_book_index_manager(self, indexname="prealgebra"):
		return self.books.get(indexname)

	def user_index_exists(self, username, typeName):
		indexname = UserIndexManager.content_indexname(username, typeName, self.use_md5)
		return self.storage.index_exists(indexname, username=username)

	def get_user_index_manager(self, username=None, create=True):
		"""
		:param create: If true (the default) an index will be created if needed.
		"""
		if username:
			# FIXME: We don't want to clog self.users with unneeded indexes (DoS)
			# and we'd also like to age out old but unneeded ones. We don't
			# have a great way of knowing if there's any index for the user (?)
			# so we're hardcoding a type
			if not self.users.has_key(username) and (self.user_index_exists(username, 'Note') or create):
				um = UserIndexManager(username, self.storage, self.use_md5)
				for n in IndexableContentMetaclass.indexables:
					instance_type = content_type_class(n)()
					if instance_type.get_schema():
						um.register_index(n)
				self.users[username] = um
			return self.users.get(username)


	##############################

	def content_search(self, query, limit=None, indexname="prealgebra"):
		bm = self.get_book_index_manager(indexname)
		results = bm.search(query, limit) if (bm and query) else None
		return results if results else empty_search_result(query)

	def content_quick_search(self, query, limit=None, indexname="prealgebra"):
		bm = self.get_book_index_manager(indexname)
		results = bm.quick_search(query, limit) if (bm and query) else None
		return results if results else empty_search_result(query)

	def content_suggest_and_search(self, query, limit=None, indexname="prealgebra"):
		bm = self.get_book_index_manager(indexname)
		results = bm.suggest_and_search(query, limit) if (bm and query) else None
		return results if results else empty_suggest_and_search_result(query)

	def content_suggest(self, word, limit=None, maxdist=None, prefix=None,indexname="prealgebra"):
		bm = self.get_book_index_manager(indexname)
		results = bm.suggest(word, limit=limit, maxdist=maxdist, prefix=prefix) if (bm and word) else None
		return results if results else empty_suggest_result(word)

	search = content_search
	suggest = content_suggest
	quick_search = content_search
	suggest_and_search = content_suggest_and_search

	
	##########################
	
	def get_user(self, username):
		result = None
		if self.dataserver:
			with self.dataserver.dbTrans():
				result = self.dataserver.root['users'].get(username, None)
		return result
	
	def get_user_communities(self, username):
		user = self.get_user(username)
		return list(user.communities) if user else []

	##############################

	# descriptor and decorator
	class descriptor(object):
		def __init__(self, func):
			self.func = func

		def __call__(self, *args, **kargs):
			with IndexManager.get_shared_indexmanager().dbTrans():
				return self.func(*args, **kargs)

		def __get__(self, instance, owner):
			def wrapper(*args, **kargs):
				return self(instance, *args, **kargs)
			return wrapper

	@descriptor
	def _execute_user_search(self, search_method, username, *args, **kwargs):
		um = self.get_user_index_manager(username)
		results = search_method(um,  *args, **kwargs) if um else None
		return results
	
	def user_data_search(self, query, limit=None, username=None, search_on=None):
		results = None
		if query:
			jobs = []
			for name in [username] + self.get_user_communities(username):
				jobs.append(gevent.spawn(self._execute_user_search, UserIndexManager.search, name, query, limit, search_on))
			gevent.joinall(jobs)
			for job in jobs:
				results = merge_search_results (results, job.value)
		return results if results else empty_search_result(query)

	def user_data_quick_search(self, query, limit=None, username=None, search_on=None):	
		results = None
		if query:
			jobs = []
			for name in [username] + self.get_user_communities(username):
				jobs.append(gevent.spawn(self._execute_user_search, UserIndexManager.quick_search, name, query, limit, search_on))
			gevent.joinall(jobs)
			for job in jobs:
				results = merge_search_results (results, job.value)
		return results if results else empty_search_result(query)

	def user_data_suggest_and_search(self, query, limit=None, username=None, search_on=None):	
		results = None
		if query:
			jobs = []
			for name in [username] + self.get_user_communities(username):
				jobs.append(gevent.spawn(self._execute_user_search, UserIndexManager.suggest_and_search, name, query, limit, search_on))
			gevent.joinall(jobs)
			for job in jobs:
				results = merge_suggest_and_search_results (results, job.value)
		return results if results else empty_suggest_and_search_result(query)

	def user_data_suggest(self, word, limit=None, maxdist=None, prefix=None, username=None, search_on=None ):
		results = None
		if word:
			jobs = []
			for name in [username] + self.get_user_communities(username):
				jobs.append(gevent.spawn(self._execute_user_search, UserIndexManager.suggest, name, word, \
										 limit=limit, maxdist=maxdist, prefix=prefix, search_on=search_on))
			gevent.joinall(jobs)
			for job in jobs:
				results = merge_suggest_results (results, job.value)
		return results if results else empty_suggest_result(word)

	##############################
	
	def _check_user_content(self, data, username):
		if 'Creator' not in data:
			data['Creator'] = username
		return data
	
	@descriptor
	def index_user_content(self, externalValue, username, typeName="Notes"):
		um = self.get_user_index_manager(username)
		if um: um.index_content(self._check_user_content(externalValue, username), typeName)

	@descriptor
	def update_user_content(self, externalValue, username, typeName="Notes"):
		um = self.get_user_index_manager(username)
		if um: um.update_content(self._check_user_content(externalValue, username), typeName)

	@descriptor
	def delete_user_content(self, externalValue, username, typeName="Notes"):
		um = self.get_user_index_manager(username)
		if um: um.delete_content(externalValue, typeName)

	@descriptor
	def externalize(self, username, typeName="Notes"):
		um = self.get_user_index_manager(username)
		if um: um.externalize(typeName)

	##########################

	@classmethod
	def onChange(cls, datasvr, msg, username=None, broadcast=None):
		if username:
			obj = getattr(msg, "object", None)
			if obj and contenttypes.__dict__.has_key(obj.__class__.__name__):
				data = obj
				if callable( getattr( obj, 'toExternalObject', None ) ):
					data = obj.toExternalObject()
				cls.get_shared_indexmanager()._indexagent.add_event(creator=username,
																	changeType=msg.type,
																	dataType=obj.__class__.__name__,
																	data=data )

	##########################

	@descriptor
	def remove_user(self, username):
		um = self.users.pop(username, None)
		if um: um.close()

	@descriptor
	def optimize_user_index(self, username, typeName='Notes'):
		um = self.users.pop(username, None)
		if um: um.optimize_index(typeName)

	def optimize_user_indices(self, username):
		for n in IndexableContentMetaclass.indexables:
			self.optimize_user_index(username, n)

	@descriptor
	def _close_ums(self):
		for um in self.users.itervalues():
			um.close()
		self.users.clear()

	def close(self):
		for bm in self.books.itervalues():
			bm.close()
		self._close_ums()
		self._indexagent.close()

	def __del__(self):
		self.close()

##########################

def create_directory_index_manager(user_index_dir="/tmp", usernames=None, use_md5=True):
	"""
	Create a directory based index manager"
	user_index_dir: location of user indices
	usernames: user names to initialize
	use_md5: flag to md5 has the indices names
	"""
	
	logger.info("Creating a directory based index manager '%s'", user_index_dir)
	
	if user_index_dir == '/tmp' and 'DATASERVER_DIR' in os.environ:
		user_index_dir = os.environ['DATASERVER_DIR']
		
	im = IndexManager(storage=create_directory_index_storage(user_index_dir), use_md5=use_md5)
	if usernames:
		for username, name in [(u, n) for u in usernames for n in IndexableContentMetaclass.indexables]:
			if im.user_index_exists(username, name):
				im.get_user_index_manager(username)

	return im

def create_zodb_index_manager(	db,
								indicesKey ='__indices',
								blobsKey = "__blobs",
				 				use_lock_file = False,
				 				lock_file_dir = "/tmp/locks",
				 				use_md5 = False,
				 				dataserver = None):
	"""
	Create a ZODB based index manager.
	db: zodb database
	indicesKey: Entry in root where index names are to be stored
	blobsKey: Entry in root where blobs are saved
	use_lock_file: flag to use file locks
	lock_file_dir: location where file locks will reside
	use_md5: flag to md5 has the indices names
	dataserver: Application DataServer (nti.dataserver)
	"""

	logger.info("Creating a zodb based index manager (index=%s, blobs=%s)", indicesKey, blobsKey)

	storage = create_zodb_index_storage(db = db,
										indicesKey =indicesKey,
										blobsKey = blobsKey,
										use_lock_file = use_lock_file,
										lock_file_dir = lock_file_dir)

	im = IndexManager(storage=storage, use_md5=use_md5, dataserver=dataserver)
	return im

create_index_manager = create_directory_index_manager
