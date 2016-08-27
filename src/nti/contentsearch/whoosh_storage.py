#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Whoosh index storage.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import time
import random
import tempfile

from zope import interface

from persistent import Persistent

from whoosh import index

from whoosh.filedb.filestore import FileStorage as WhooshFileStorage

from whoosh.index import LockError
from whoosh.index import _DEF_INDEX_NAME

from nti.externalization.representation import WithRepr

from nti.property.property import CachedProperty

from nti.schema.eqhash import EqHash

from .interfaces import IWhooshIndexStorage

# segment writer
max_segments = 10
merge_first_segments = 5

def segment_merge(writer, segments):

	from whoosh.reading import SegmentReader
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

@interface.implementer(IWhooshIndexStorage)
class IndexStorage(Persistent):

	default_ctor_args = writer_ctor_args
	default_commit_args = writer_commit_args

	def create_index(self, indexname, schema):
		raise NotImplementedError()

	def index_exists(self, indexname):
		raise NotImplementedError()

	def get_index(self, indexname):
		if self.index_exists(indexname):
			return self.open_index(indexname=indexname)
		return None

	def get_or_create_index(self, indexname, schema=None, recreate=True):
		raise NotImplementedError()

	def open_index(self, indexname, schema=None):
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
	if not indexdir:
		dsdir = os.getenv('DATASERVER_DIR') or tempfile.gettempdir()
		indexdir = os.path.join(dsdir, 'data', "indexes")

	indexdir = os.path.expanduser(indexdir)
	if not os.path.exists(indexdir):
		os.makedirs(indexdir)
	return indexdir

@WithRepr
@EqHash("folder",)
class DirectoryStorage(IndexStorage):

	def __init__(self, indexdir=None):
		self.folder = prepare_index_directory(indexdir)

	def create_index(self, schema, indexname=_DEF_INDEX_NAME):
		self.makedirs()
		return self.storage.create_index(schema, indexname)

	def index_exists(self, indexname=_DEF_INDEX_NAME):
		path = self.get_folder()
		return index.exists_in(path, indexname)

	def get_or_create_index(self, indexname=_DEF_INDEX_NAME, schema=None,
							recreate=False):
		recreate = self.makedirs() or recreate
		if not self.index_exists(indexname):
			recreate = True

		if recreate:
			return self.create_index(schema=schema, indexname=indexname)

		return self.open_index(indexname=indexname)

	def open_index(self, indexname, schema=None):
		return self.storage.open_index(indexname=indexname)

	@CachedProperty('folder')
	def storage(self):
		path = self.get_folder()
		return WhooshFileStorage(path)

	def __getstate__(self):
		# FIXME: Although everything pickles fine,
		# we are not robust to the locations of the paths
		# changing between machines. We need to be storing
		# the nti.contentlibrary IKey path, which
		# is robust across machines or changing directory
		# layouts.
		state = super(DirectoryStorage,self).__getstate__()
		if 'storage' in state:
			del state['storage']
		return state

	def makedirs(self):
		path = self.get_folder()
		if not os.path.exists(path):
			os.makedirs(path)
			return path
		return False

	def get_folder(self):
		return self.folder

	def __str__(self):
		return self.folder

def create_directory_index(indexname, schema, indexdir=None, close_index=True):
	storage = DirectoryStorage(indexdir)
	idx = storage.get_or_create_index(indexname=indexname, schema=schema)
	if close_index:
		idx.close()
	return idx, storage
