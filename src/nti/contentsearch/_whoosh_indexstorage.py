from __future__ import print_function, unicode_literals

import os
import fcntl
import binascii

from zope import interface

from whoosh import index
from whoosh.index import _DEF_INDEX_NAME
from whoosh.filedb.structfile import StructFile
from whoosh.filedb.filestore import FileStorage as WhooshFileStorage

from nti.contentsearch.interfaces import IWhooshIndexStorage

import logging
logger = logging.getLogger( __name__ )

def oid_to_path(oid, max_bytes=2):
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
	
# segment writer
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

# limitmb: http://packages.python.org/Whoosh/batch.html
default_ctor_args = {'limitmb':96}
default_commit_args = {'merge':False, 'optimize':False, 'mergetype':segment_merge}
	
class IndexStorage(object):
	interface.implements(IWhooshIndexStorage)
	
	def create_index(self, indexname, schema, *args, **kwargs):
		raise NotImplementedError()
	
	def index_exists(self, indexname, *args, **kwargs):
		raise NotImplementedError()
	
	def get_index(self, indexname, *args, **kwargs):
		raise NotImplementedError()
	
	def get_or_create_index(self, indexname, schema=None, recreate=True, *args, **kwargs):
		raise NotImplementedError()
	
	def open_index(self, indexname, schema=None, *args, **kwargs):
		raise NotImplementedError()
	
	def storage(self, *args, **kwargs):
		raise NotImplementedError()
	
	def ctor_args(self, *args, **kwargs):
		"""
		Return a dictionary with the arguments to be passed to an 
		index writer constructor
		""" 
		return default_ctor_args
	
	def commit_args(self, *args, **kwargs):
		"""
		Return a dictionary with the arguments to be passed to an 
		index writer commit method
		""" 
		return default_commit_args

class DirectoryStorage(IndexStorage):
	
	def __init__(self, indexdir="/tmp"):
		if not os.path.exists(indexdir):
			os.makedirs(indexdir)
		self.folder = indexdir
	
	def create_index(self, schema, indexname=_DEF_INDEX_NAME, *args, **kwargs):
		self.makedirs(**kwargs)
		return self.storage(**kwargs).create_index(schema, indexname)
		
	def index_exists(self, indexname=_DEF_INDEX_NAME, *args, **kwargs):
		path = self.get_folder(**kwargs)
		return index.exists_in(path, indexname)
	
	def get_index(self, indexname=_DEF_INDEX_NAME, *args, **kwargs):
		if self.index_exists(indexname, **kwargs):
			return self.open_index(indexname=indexname, *args, **kwargs)
		else:
			return None
	
	def get_or_create_index(self, indexname=_DEF_INDEX_NAME, schema=None, recreate=False, *args, **kwargs):
		recreate = self.makedirs(**kwargs) or recreate
		if not self.index_exists(indexname, *args, **kwargs):
			recreate = True
			
		if recreate:
			return self.create_index(schema=schema, indexname=indexname, *args, **kwargs)
		else:
			return self.open_index(indexname=indexname, **kwargs)

	def open_index(self, indexname, schema=None, *args, **kwargs):
		return self.storage(**kwargs).open_index(indexname=indexname)
	
	def storage(self, *args, **kwargs):
		s = getattr(self, "_storage", None)
		if not s:
			path = self.get_folder(*args, **kwargs)
			self._storage = WhooshFileStorage(path)
			s = self._storage
		return s
	
	def makedirs(self, *args, **kwargs):
		path = self.get_folder(*args, **kwargs)
		if not os.path.exists(path):
			os.makedirs(path)
			return True
		else:
			return False
		
	def get_folder(self, *args, **kwargs):
		return self.folder

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
		return oid_to_path(oid, max_bytes)
	
def open_file(self, name, *args, **kwargs):
	try:
		f = open(self._fpath(name), "rb")
		fd = f.fileno()
		fl = fcntl.fcntl(fd, fcntl.F_GETFL)
		fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
		return StructFile(f, name=name, *args, **kwargs)
	except:
		raise
			
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

