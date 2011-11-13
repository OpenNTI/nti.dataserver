import logging
logger = logging.getLogger( __name__ )


import time
import inspect
import os
from hashlib import md5

from whoosh.store import LockError
from whoosh import index

from _indexagent import IndexAgent
import contenttypes
from contenttypes import empty_search_result
from contenttypes import empty_suggest_result
from contenttypes import empty_suggest_and_search_result
from contenttypes import merge_search_results
from contenttypes import merge_suggest_results
from contenttypes import Book
from indexstorage import create_directory_index_storage
from indexstorage import create_zodb_index_storage

#########################

__all__ = ['UserIndexManager', 'BookIndexManager', 'IndexManager',
		   'create_directory_index_manager', 'create_zodb_index_manager']

#########################

_instances = {}
def singleton(cls):
	if cls not in _instances:
		_instances[cls] = cls()
	return _instances[cls]

def content_type_class(typeName='Notes'):
	className = typeName[0:-1] if typeName.endswith('s') else typeName
	if className in contenttypes.__dict__:
		result = contenttypes.__dict__[className]
	else:
		result = contenttypes.UserIndexableContent
	return result

_indexables = []
for k, v in contenttypes.__dict__.items():
	if inspect.isclass(v) and issubclass(v, contenttypes.UserIndexableContent) and \
		getattr(v, '__indexable__', False):

		_indexables.append(k)

##########################

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
		return 'IndexTypeMixin(user=%s, type=%s)' %  (self.username, self.type_instance)

from zope import interface

class IUserIndexManager(interface.Interface):
	pass

class UserIndexManager(object):
	interface.implements(IUserIndexManager)
	def __init__(self, username, index_storage, use_md5=True,delay=0.25):
		self.username = username
		self.indices = {}
		self.delay = delay
		self.use_md5 = use_md5
		self.index_storage = index_storage

	def __str__( self ):
		return self.username

	def __repr__( self ):
		return 'UserIndexManager(user=%s, indices=%s, storage=%s)' % (self.username, self.indices, self.index_storage)

	@property
	def storage(self):
		return self.index_storage

	def get_content_type(self,  typeName='Notes', indexname=None):
		if not indexname:
			indexname = self.get_content_indexname(typeName)
		return self.indices[indexname].instance if self.indices.has_key(indexname) else None

	def __ctor_args(self):
		return self.storage.ctor_args(username=self.username)

	def get_writer(self, index):
		writer = None
		while writer is None:
			try:
				writer = index.writer(**self.__ctor_args())
			except LockError:
				time.sleep(self.delay)
		return writer

	def get_content_writer(self, typeName='Notes', indexname=None):
		if not indexname:
			indexname = self.get_content_indexname(typeName)
		return self.get_writer(self.indices[indexname].index) if self.indices.has_key(indexname) else None

	def get_content_searcher(self, typeName='Notes'):
		index = self.get_content_index(typeName, False)
		return index.searcher() if index else None

	@classmethod
	def content_indexname(cls, username, typeName='Notes', use_md5=True):
		content_type = content_type_class(typeName)
		if use_md5:
			m = md5()
			m.update(username)
			m.update(content_type.__name__.lower())
			indexname = str(m.hexdigest())
		else:
			indexname = username + "_" + content_type.__name__.lower()

		return indexname

	def get_content_indexname(self, typeName='Notes'):
		return self.content_indexname(self.username, typeName, self.use_md5)

	def get_content_index(self, typeName='Notes', create=True):
		indexname = self.get_content_indexname(typeName)
		if not self.indices.has_key(indexname):

			if not create: return None

			type_instance = singleton(content_type_class(typeName))
			schema = type_instance.get_schema()
			if not schema: return None

			idx = self.storage.get_or_create_index(indexname=indexname, schema=schema, username=self.username)
			self.indices[indexname] = IndexTypeMixin(type_instance, idx)

			logger.debug("Index '%s' was created for user %s to store %s objects",\
						 indexname, self.username, type_instance.__class__.__name__)

		return self.indices[indexname]

	def register_index(self, typeName='Notes', auto_create=True):
		indexname = self.get_content_indexname(typeName)
		if not self.indices.has_key(indexname):

			type_instance = singleton(content_type_class(typeName))
			if auto_create:
				schema = type_instance.get_schema()
				if not schema: return
				idx = self.storage.get_or_create_index(indexname=indexname, schema=schema, username=self.username)
			else:
				idx = self.storage.get_index(indexname=indexname, username=self.username)

			if idx:
				self.indices[indexname] = IndexTypeMixin(type_instance, idx)
				logger.debug("Index '%s' was registered to user %s to store %s objects",\
						 	 indexname, self.username, type_instance.__class__.__name__)

	##########################

	def _adapt_search_on(self, search_on=None):
		if search_on:
			lm = lambda x: x[0:-1] if x.endswith('s') else x
			search_on = [lm(x) for x in search_on]
		return search_on

	def search(self, query, limit=None, search_on=None):
		results = None
		search_on = self._adapt_search_on(search_on)
		for t in self.indices.itervalues():
			if not search_on or t.type_name in search_on:
				with t.index.searcher() as searcher:
					rs = t.instance.search(searcher=searcher, query=query, limit=limit)
					results = merge_search_results(results, rs)
		return results if results else empty_search_result(query)

	def quick_search(self, query, limit=None, search_on=None):
		results = None
		search_on = self._adapt_search_on(search_on)
		for t in self.indices.itervalues():
			if not search_on or t.type_name in search_on:
				with t.index.searcher() as searcher:
					rs = t.instance.quick_search(searcher=searcher, query=query, limit=limit)
					results = merge_search_results(results, rs)
		return results if results else empty_search_result(query)

	def suggest_and_search(self, query, limit=None, search_on=None):
		results = None
		search_on = self._adapt_search_on(search_on)
		for t in self.indices.itervalues():
			if not search_on or t.type_name in search_on:
				with t.index.searcher() as searcher:
					rs = t.instance.suggest_and_search(searcher=searcher, query=query, limit=limit)
					results = merge_search_results(results, rs)
		return results if results else empty_suggest_and_search_result(query)

	def suggest(self, word, limit=None, maxdist=None, prefix=None, search_on=None):
		results = None
		search_on = self._adapt_search_on(search_on)
		for t in self.indices.itervalues():
			if not search_on or t.type_name in search_on:
				with t.index.searcher() as searcher:
					rs = t.instance.suggest(searcher=searcher, word=word,\
											limit=limit, maxdist=maxdist, prefix=prefix)
					results = merge_suggest_results(results, rs)
		return results if results else empty_suggest_result(word)

	##########################

	def index_content(self, externalValue, typeName='Notes'):
		t = self.get_content_index(typeName, True)
		if t:
			writer = self.get_content_writer(indexname=t.indexname)
			t.instance.index_content(writer, externalValue, **self.__commit_args())

	def update_content(self, externalValue, typeName='Notes'):
		t = self.get_content_index(typeName, True)
		if t:
			writer = self.get_content_writer(indexname=t.indexname)
			t.instance.update_content(writer, externalValue, **self.__commit_args())

	def delete_content(self, externalValue, typeName='Notes'):
		t = self.get_content_index(typeName, False)
		if t:
			writer = self.get_content_writer(indexname=t.indexname)
			t.instance.delete_content(writer, externalValue, **self.__commit_args())

	def __commit_args(self):
		return self.storage.commit_args(username=self.username)

	##########################

	def _close_index(self, idx):
		idx.optimize()
		idx.close()

	def remove_index(self, typeName='Notes'):
		t = self.get_content_index(typeName, False)
		if t: self._close_index(t.index)

	def optimize_index(self, typeName='Notes'):
		t = self.get_content_index(typeName, False)
		if t: t.index.optimize()

	def close(self):
		for t in self.indices.itervalues():
			self._close_index(t.index)
		self.indices.clear()

##########################

class IBookIndexManager(interface.Interface):
	pass

class BookIndexManager(object):
	interface.implements( IBookIndexManager )
	def __init__(self, indexdir="/tmp/", indexname="prealgebra"):
		self.indexdir = indexdir
		self._book = IndexTypeMixin(Book(), create_directory_index_storage(indexdir).get_index(indexname) )

	@property
	def book(self):
		return self._book.instance

	@property
	def bookidx(self):
		return self._book.index

	@property
	def indexname(self):
		return self.bookidx.indexname

	##########################

	def search(self, query, limit=None):
		with self.bookidx.searcher() as s:
			results = self.book.search(s, query, limit)
		return results

	def quick_search(self, query, limit=None):
		with self.bookidx.searcher() as s:
			results = self.book.quick_search(s, query, limit)
		return results

	def suggest_and_search(self, query, limit=None):
		with self.bookidx.searcher() as s:
			results = self.book.suggest_and_search(s, query, limit)
		return results

	def suggest(self, word, limit=None, maxdist=None, prefix=None):
		with self.bookidx.searcher() as s:
			results = self.book.suggest(s, word, limit=limit, maxdist=maxdist, prefix=prefix)
		return results

	##########################

	def close(self):
		self.bookidx.close()

	def __del__(self):
		try:
			self.close()
		except:
			pass

class IIndexManager(interface.Interface):
	pass


class IndexManager(object):
	"""
	Provides a basic index manager
	"""
	interface.implements(IIndexManager)
	indexmanager = None

	@classmethod
	def get_shared_indexmanager(cls):
		return cls.indexmanager

	##############################

	def __new__(cls, *args, **kwargs):
		if not cls.indexmanager:
			cls.indexmanager = super(IndexManager, cls).__new__(cls, *args, **kwargs)
		return cls.indexmanager

	def __init__(self, storage=None, use_md5=True, user_index_dir="/tmp"):
		self.books = {}
		self.users = {}
		self.use_md5 = use_md5
		self.storage = storage or create_directory_index_storage(user_index_dir)
		self._indexagent = IndexAgent( self )

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
		return self.books[indexname] if self.books.has_key(indexname) else None

	def user_index_exists(self, username, typeName):
		indexname = UserIndexManager.content_indexname(username, typeName, self.use_md5)
		return self.storage.index_exists(indexname, username=username)

	def get_user_index_manager(self, username=None):
		if username:
			if not self.users.has_key(username):
				um = UserIndexManager(username, self.storage, self.use_md5)
				for n in _indexables:
					instance_type = content_type_class(n)()
					if instance_type.get_schema():
						um.register_index(n)
				self.users[username] = um
			return self.users[username]
		else:
			return None

	##############################

	def content_search(self, query, limit=None, indexname="prealgebra"):
		bm=self.get_book_index_manager(indexname)
		results=bm.search(query, limit) if bm else None
		return results if results else empty_search_result(query)

	def content_quick_search(self, query, limit=None, indexname="prealgebra"):
		bm = self.get_book_index_manager(indexname)
		results = bm.quick_search(query, limit) if bm else None
		return results if results else empty_search_result(query)

	def content_suggest_and_search(self, query, limit=None, indexname="prealgebra"):
		bm = self.get_book_index_manager(indexname)
		results = bm.suggest_and_search(query, limit) if bm else None
		return results if results else empty_suggest_and_search_result(query)

	def content_suggest(self, word, limit=None, maxdist=None, prefix=None,indexname="prealgebra"):
		bm = self.get_book_index_manager(indexname)
		results = bm.suggest(word, limit=limit, maxdist=maxdist, prefix=prefix) if bm else None
		return results if results else empty_suggest_result(word)

	search = content_search
	suggest = content_suggest
	quick_search = content_search
	suggest_and_search = content_suggest_and_search

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
	def user_data_search(self, query, limit=None, username=None, search_on=None):
		um = self.get_user_index_manager(username)
		results = um.search(query, limit, search_on) if um else None
		return results if results else empty_search_result(query)

	@descriptor
	def user_data_quick_search(self, query, limit=None, username=None, search_on=None):
		um = self.get_user_index_manager(username)
		results = um.quick_search(query, limit, search_on) if um else None
		return results if results else empty_search_result(query)

	@descriptor
	def user_data_suggest_and_search(self, query, limit=None, username=None, search_on=None):
		um = self.get_user_index_manager(username)
		results = um.suggest_and_search(query, limit, search_on) if um else None
		return results if results else empty_suggest_and_search_result(query)

	@descriptor
	def user_data_suggest(self, word, limit=None, maxdist=None, prefix=None,\
						username=None, search_on=None ):
		um = self.get_user_index_manager(username)
		results = um.suggest( word, limit=limit, maxdist=maxdist,
							  prefix=prefix, search_on=search_on) if um else None
		return results if results else empty_suggest_result(word)


	@descriptor
	def index_user_content(self, externalValue, username, typeName="Notes"):
		um = self.get_user_index_manager(username)
		if um: um.index_content(externalValue, typeName)

	@descriptor
	def update_user_content(self, externalValue, username, typeName="Notes"):
		um = self.get_user_index_manager(username)
		if um: um.update_content(externalValue, typeName)

	@descriptor
	def delete_user_content(self, externalValue, username, typeName="Notes"):
		um = self.get_user_index_manager(username)
		if um: um.delete_content(externalValue, typeName)

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
		for n in _indexables:
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
	if user_index_dir == '/tmp' and 'DATASERVER_DIR' in os.environ:
		user_index_dir = os.environ['DATASERVER_DIR']
	im = IndexManager(storage=create_directory_index_storage(user_index_dir), use_md5=use_md5)
	if usernames:
		for username, name in [(u, n) for u in usernames for n in _indexables]:
			if im.user_index_exists(username, name):
				im.get_user_index_manager(username)

	return im

def create_zodb_index_manager(	db,\
								indicesKey='__indices',\
								blobsKey="__blobs",\
				 				use_lock_file=False,\
				 				lock_file_dir="/tmp/locks",
				 				use_md5=False):
	"""
	Create a ZODB based index manager.
	db: zodb database
	indicesKey: Entry in root where index names are to be stored
	blobsKey: Entry in root where blobs are saved
	use_lock_file: flag to use file locks
	lock_file_dir: location where file locks will reside
	use_md5: flag to md5 has the indices names
	"""

	storage = create_zodb_index_storage(db=db,\
										indicesKey=indicesKey,\
										blobsKey=blobsKey,\
										use_lock_file=use_lock_file,\
										lock_file_dir=lock_file_dir)

	im = IndexManager(storage=storage, use_md5=use_md5)
	return im

create_index_manager = create_directory_index_manager
