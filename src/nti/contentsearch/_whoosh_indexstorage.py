# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import os
import time
import random
import binascii

from zope import interface

from whoosh import index
from whoosh.store import LockError
from whoosh.index import _DEF_INDEX_NAME
from whoosh.filedb.filestore import FileStorage as WhooshFileStorage

from nti.contentsearch import interfaces as search_interfaces

def oid_to_path(oid, max_bytes=3):
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

def get_index_writer(index, writer_ctor_args={}, maxiters=40, delay=0.25):
	counter = 0
	writer = None
	while writer is None:
		try:
			writer = index.writer(**writer_ctor_args)
		except LockError, e:
			counter += 1
			if counter <= maxiters:
				x = random.uniform(0.1, delay)
				time.sleep(x)
			else:
				raise e
	return writer

# limitmb: http://packages.python.org/Whoosh/batch.html
writer_ctor_args = {'limitmb':96}
writer_commit_args = {'merge':False, 'optimize':False, 'mergetype':segment_merge}

@interface.implementer( search_interfaces.IWhooshIndexStorage )
class IndexStorage(object):

	default_ctor_args = writer_ctor_args
	default_commit_args = writer_commit_args

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
		return self.default_ctor_args

	def commit_args(self, *args, **kwargs):
		"""
		Return a dictionary with the arguments to be passed to an
		index writer commit method
		"""
		return self.default_commit_args

def prepare_index_directory(indexdir=None):
	dsdir = os.getenv('DATASERVER_DIR', "/tmp")
	indexdir = os.path.join(dsdir, "indicies") if not indexdir else indexdir
	indexdir = os.path.expanduser(indexdir)
	if not os.path.exists(indexdir):
		os.makedirs(indexdir)
	return indexdir

class DirectoryStorage(IndexStorage):

	def __init__(self, indexdir=None):
		self.folder = prepare_index_directory(indexdir)

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

class UserDirectoryStorage(DirectoryStorage):

	def __init__(self, indexdir=None, max_level=3):
		super(UserDirectoryStorage, self).__init__(indexdir)
		self.stores = {}
		self.max_level = max_level

	def storage(self, **kwargs):
		username = kwargs.get('username', None)
		if not username:
			return super(UserDirectoryStorage, self).storage()
		else:
			key = self.oid_to_path(username, self.max_level)
			if not self.stores.has_key(key):
				path = os.path.join(self.folder, key)
				self.stores[key] = WhooshFileStorage(path)
			return self.stores[key]

	def get_folder(self, **kwargs):
		username = kwargs.get('username', None)
		if username:
			path = self.oid_to_path(username, self.max_level)
			path = os.path.join(self.folder, path)
			return path
		return self.folder

	def oid_to_path(self, oid, max_bytes=3):
		return oid_to_path(oid, max_bytes)


def create_directory_index(indexname, schema, indexdir=None, close_index=True):
	storage = DirectoryStorage(indexdir)
	idx = storage.get_or_create_index(indexname=indexname, schema=schema)
	if close_index:
		idx.close()
	return idx, storage

@interface.implementer( search_interfaces.IWhooshIndexStorage )
def _create_default_whoosh_storage():
	if os.getenv('DATASERVER_DIR', None):
		return UserDirectoryStorage()
	return None
