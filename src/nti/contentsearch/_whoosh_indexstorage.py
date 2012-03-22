import os
import fcntl
import binascii
import transaction
from threading import Lock

import zc.lockfile
from zope import interface

from ZODB import DB
from ZODB.blob import Blob
from persistent.mapping import PersistentMapping

from whoosh import index
from whoosh.store import Storage as WhooshStorage
from whoosh.index import _DEF_INDEX_NAME
from whoosh.filedb.filestore import FileStorage as WhooshFileStorage
from whoosh.filedb.filewriting import SegmentWriter
from whoosh.filedb.fileindex import FileIndex
from whoosh.filedb.fileindex import _create_index
from whoosh.filedb.structfile import StructFile

from nti.contentsearch import NoOpCM
from nti.contentsearch.interfaces import IWhooshIndexStorage

# -----------------------------

max_segments = 10
merge_first_segments = 5

def segment_merge(writer, segments):
		
	from whoosh.filedb.filereading import SegmentReader
	if len(segments) <= max_segments:
		return segments
	
	newsegments = []
	sorted_segment_list = sorted(segments, key=lambda s: s.doc_count_all())

	for i, s in enumerate(sorted_segment_list):
		if i < merge_first_segments:
			reader = SegmentReader(writer.storage, writer.schema, s)
			writer.add_reader(reader)
			reader.close()
		else:
			newsegments.append(s)
	return newsegments

class IndexStorage(object):
	interface.implements(IWhooshIndexStorage)
	
	"""
	Defines a basic index index storage object
	"""
	
	# limitmb: http://packages.python.org/Whoosh/batch.html
	default_ctor_args = {'limitmb':96}
	
	default_commit_args = {'merge':False, 'optimize':False, 'mergetype':segment_merge}
	
	def create_index(self, indexname, schema, **kwargs):
		raise NotImplementedError()
	
	def index_exists(self, indexname, **kwargs):
		raise NotImplementedError()
	
	def get_index(self, indexname, **kwargs):
		raise NotImplementedError()
	
	def get_or_create_index(self, indexname, schema=None, recreate=True, **kwargs):
		raise NotImplementedError()
	
	def open_index(self, indexname, schema=None, **kwargs):
		raise NotImplementedError()
	
	def dbTrans(self):
		raise NotImplementedError()
	
	def storage(self, **kwargs):
		raise NotImplementedError()
	
	def ctor_args(self, **kwargs):
		"""
		Return a dictionary with the arguments to be passed to an 
		index writer constructor
		""" 
		return self.default_ctor_args
	
	def commit_args(self, **kwargs):
		"""
		Return a dictionary with the arguments to be passed to an 
		index writer commit method
		""" 
		return self.default_commit_args

# -----------------------------

class DirectoryStorage(IndexStorage):
	
	def __init__(self, indexdir="/tmp"):
		if not os.path.exists(indexdir):
			os.makedirs(indexdir)
		self.folder = indexdir
	
	def dbTrans(self):
		return NoOpCM()
	
	def create_index(self, schema, indexname=_DEF_INDEX_NAME, **kwargs):
		self.makedirs(**kwargs)
		return self.storage(**kwargs).create_index(schema, indexname)
		
	def index_exists(self, indexname=_DEF_INDEX_NAME, **kwargs):
		path = self.get_folder(**kwargs)
		return index.exists_in(path, indexname)
	
	def get_index(self, indexname=_DEF_INDEX_NAME, **kwargs):
		if self.index_exists(indexname, **kwargs):
			return self.open_index(indexname=indexname, **kwargs)
		else:
			return None
	
	def get_or_create_index(self, indexname=_DEF_INDEX_NAME, schema=None, recreate=False, **kwargs):
		recreate = self.makedirs(**kwargs) or recreate
		if not self.index_exists(indexname, **kwargs):
			recreate = True
			
		if recreate:
			return self.create_index(schema=schema, indexname=indexname, **kwargs)
		else:
			return self.open_index(indexname=indexname, **kwargs)

	def open_index(self, indexname, schema=None, **kwargs):
		return self.storage(**kwargs).open_index(indexname=indexname)
	
	def storage(self, **kwargs):
		s = getattr(self, "_storage", None)
		if not s:
			path = self.get_folder(**kwargs)
			self._storage = WhooshFileStorage(path)
			s = self._storage
		return s
	
	def makedirs(self, **kwargs):
		path = self.get_folder(**kwargs)
		if not os.path.exists(path):
			os.makedirs(path)
			return True
		else:
			return False
		
	def get_folder(self, **kwargs):
		return self.folder

# -----------------------------

class MultiDirectoryStorage(DirectoryStorage):
	
	def __init__(self, indexdir="/tmp", max_level=2):
		super(MultiDirectoryStorage, self).__init__(indexdir=indexdir)
		self.stores = {}
		self.max_level = max_level
	
	def get_param(self, **kwargs):
		return kwargs.get('username', None)
	
	def storage(self, **kwargs):
		un = self.get_param(**kwargs)
		if not un:
			return super(MultiDirectoryStorage, self).storage(**kwargs) 
		else:
			key = self.oid_to_path(un, self.max_level)
			if not self.stores.has_key(key):
				path = os.path.join(self.folder, key)
				self.stores[key] = WhooshFileStorage(path)
			return self.stores[key]
		
	def get_folder(self, **kwargs):
		un = self.get_param(**kwargs)
		if un:
			path = self.oid_to_path(un, self.max_level)
			path = os.path.join(self.folder, path)
			return path
		else:
			return self.folder
	
	def oid_to_path(self, oid, max_bytes=2):
		"""
		Taken from ZODB/blob.py/BushyLayout
		"""
		count = 0
		directories = []
		for byte in str(oid):
			count = count+1
			directories.append('0x%s' % binascii.hexlify(byte))
			if count >= max_bytes: break
		return os.path.sep.join(directories)
	
	
def open_file(self, name, *args, **kwargs):
	try:
		f = open(self._fpath(name), "rb")
		fd = f.fileno()
		fl = fcntl.fcntl(fd, fcntl.F_GETFL)
		fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
		return StructFile(f, name=name, *args, **kwargs)
	except:
		raise

# ------------------------------

class ZODBIndex(FileIndex):
	"""
	ZODB Whoosh index
	"""
	
	def __init__(self, db, *args, **kargs):
		super(ZODBIndex, self).__init__(*args, **kargs)
		self.db = db
	
	def writer(self, **kwargs):
		return ZODBSegmentWriter(self.db, self, **kwargs)
	
	def close(self):
		super(ZODBIndex, self).close()
		
	def __enter__(self):
		return self
	
	def __exit__(self, t, v, tb):
		self.close()
		
class ZODBSegmentWriter(SegmentWriter):
	
	def __init__(self, db, *args, **kargs):
		super(ZODBSegmentWriter, self).__init__(*args, **kargs)
		self.db = db
	
	def commit(self, mergetype=None, optimize=False, merge=True):
		super(ZODBSegmentWriter, self).commit(mergetype=mergetype, optimize=optimize, merge=merge)
		
	def cancel(self):
		super(ZODBSegmentWriter, self).cancel()
		
	def abort(self):
		self.cancel()
		
# ------------------------------

class ZODBIndexStorage(WhooshStorage, IndexStorage):
	"""
	ZEO/ZODB based whoosh index storage. 
	"""
	def __init__(self, 
				 db, 
				 indices_key='__indices',\
				 blobs_key="__blobs",  
				 use_lock_file=False, 
				 lock_file_dir="/tmp/locks",
				 mapped=True):
		

		self.db = db 
		self.mapped = mapped
		self.blobs_key = blobs_key
		self.indices_key = indices_key
		self.transaction_manager = transaction.manager
		self.conn = self.db.open( self.transaction_manager )
		
		# create keys
		with self.dbTrans():
			for key in (indices_key, blobs_key):
				dbroot = self.root
				if not dbroot.has_key(key):
					dbroot[key] = PersistentMapping()
		
		# set lock file
		if use_lock_file and lock_file_dir:
			self.lock_file_dir = os.path.expanduser(lock_file_dir)
			if not os.path.exists(self.lock_file_dir):
				os.makedirs(self.lock_file_dir)
			self.use_lock_file = True
		else:
			self.locks = {}
			self.use_lock_file = False
		
	@property	
	def root(self):
		return self.conn.root()
	
	@property
	def indices(self):
		return self.root[self.indices_key]

	@property
	def blobs(self):
		return self.root[self.blobs_key]
	
	# ---------- IndexStorage ----------
		
	def dbTrans(self):
		return self.transaction_manager
	
	def index_exists(self, indexname, **kwargs):
		return self.indices.has_key(indexname)
	
	def get_index(self, indexname, **kwargs):
		if self.indices.has_key(indexname):
			schema = self.indices[indexname]
			return ZODBIndex(self.db, storage=self, schema=schema, indexname=indexname)
		else:
			return None
	
	def get_or_create_index(self, indexname, schema=None, recreate=False, **kwargs):
		index = self.get_index(indexname=indexname, **kwargs)
		if not index or recreate:
			index = self.create_index(indexname=indexname, schema=schema, **kwargs)
		return index
		
	def create_index(self, schema, indexname=_DEF_INDEX_NAME, **kwargs):
		_create_index(self, schema, indexname)
		self.indices[indexname] = schema
		return ZODBIndex(self.db, storage=self, schema=schema, indexname=indexname)
	
	def open_index(self, indexname=_DEF_INDEX_NAME, schema=None, **kwargs):
		index = self.get_index(indexname=indexname, **kwargs)
		if not index:
			s = "Index '%s' does not exists" % indexname
			raise IOError(s)
		return index
	
	def storage(self, **kwargs):
		return self
	
	# ---------- WhooshStorage ----------

	def create_file(self, name, excl=False, mode="w", **kwargs):
		blob = Blob()
		self.blobs[name] = blob
		fileobj = blob.open("w")
		result = StructFile(fileobj, name=name, mapped=self.mapped, **kwargs)
		return result
	
	def open_file(self, name, *args, **kwargs):
		try:
			blob = self.blobs[name]
			f = blob.open("r")
			fd = f.fileno()
			fl = fcntl.fcntl(fd, fcntl.F_GETFL)
			fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
			f = StructFile(f, name=name, *args, **kwargs)
		except:
			# print("Tried to open %r, blob=%r" % (name, self.list()))
			raise
		return f
	
	def clean(self):	
		self.blobs.clear()
		self.indices.clear()
		
	def list(self):
		try:
			files = list(self.blobs.keys())
		except:
			files = []
		
		return files
	
	def file_exists(self, name):
		return self.blobs.has_key(name)
	
	def file_modified(self, name):
		blob = self.blobs[name]
		mtime = getattr( blob, '_p_mtime', None )
		return mtime if mtime else 0
		
	def file_length(self, name):
		blob = self.blobs[name]
		esize = getattr( blob, '_p_estimated_size', None )
		return esize if esize else 0

	def delete_file(self, name):
		del self.blobs[name]
		
	def rename_file(self, frm, to, safe=False):
		if self.blobs.has_key(to):
			if safe:
				raise NameError("Blob %s exists" % to)
			else:	
				del self.blobs[to]
					
		self.blobs[to] = self.blobs[frm]
		del self.blobs[frm]
	
	def lock(self, name):
		if self.use_lock_file:
			return self._lock_file(name)
		else:
			if name not in self.locks:
				self.locks[name] = Lock()
			return self.locks[name]
	
	# -----------------------------
	
	def __str__( self ):
		return "%s,%s" % (self.indices_key,  self.blobs_key)
	
	def __repr__(self):
		return "%s(indices=%s,blobs=%s)" % (self.__class__.__name__, repr(self.indices_key), repr(self.blobs_key))
	
	# -----------------------------
	
	def close(self):
		try:
			self.conn.close()
		except:
			pass
		
	def __del__(self):
		self.close()
	
	# -----------------------------
	
	def _lock_file(self, name):
		name += ".lock"
		lockfilename = os.path.join(self.lock_file_dir, name)
		return _LockFile(lockfilename)


class _LockFile(object):
	
	def __init__(self, path):
		self.path = path
		
	def acquire(self, *args, **kargs):
		n = 0
		while True:
			try:
				return zc.lockfile.LockFile(self.path)
			except zc.lockfile.LockError:
				import time
				time.sleep(0.01)
				n += 1
				if n > 60000:
					raise Exception("Cannot aquire lock file '%s'" % self.path)
				else:
					break
				
	def release(self):
		n = 0
		while True:
			os.remove(self.path)
			if os.path.exists(self.path):
				import time
				time.sleep(0.01)
				n += 1
				if n > 60000:
					raise Exception("Cannot release lock file '%s'" % self.path)
				else:
					break
			else:
				break
			
	def __str__( self ):
		return self.path

	def __repr__( self ):
		return '_LockFile(%s)' % self.path
		
# -----------------------------
	
def create_directory_index_storage(indexdir='/tmp/indicies'):
	indexdir = os.path.expanduser(indexdir)
	if not os.path.exists(indexdir):
		os.makedirs(indexdir)
	return MultiDirectoryStorage(indexdir)
	
def create_directory_index(indexname, schema, indexdir='/tmp/indicies'):
	storage = DirectoryStorage(indexdir)
	idx = storage.get_or_create_index(indexname=indexname, schema=schema)
	idx.close()
	return idx, storage
			
# -----------------------------
		
def create_zodb_index_storage(	database, 
				 				indices_key = '__indices',\
								blobs_key = "__blobs",  
				 				use_lock_file = False, 
				 				lock_file_dir = "/tmp/locks",
								mapped=True):
		
	if isinstance(database, DB):
		storage = ZODBIndexStorage(	database, 
									indices_key = indices_key,
									blobs_key = blobs_key,
									use_lock_file = use_lock_file,
									lock_file_dir = lock_file_dir,
									mapped = mapped)		
		return storage
	else:
		raise TypeError("Invalid db type")

