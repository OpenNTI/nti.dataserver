#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import greater_than

import uuid
import random
import shutil
import tempfile

from whoosh import fields
from whoosh import query
from whoosh.compat import text_type

from .._whoosh_indexstorage import DirectoryStorage

from . import domain
from . import ConfiguringTestBase

sample_schema = fields.Schema(id=fields.ID(stored=True, unique=True),
							  content=fields.TEXT(stored=True))

class _IndexStorageTest(object):

	indexdir = None
	idx_storage = None

	@classmethod
	def tearDownClass(cls):
		shutil.rmtree(cls.indexdir, True)
		super(_IndexStorageTest, cls).tearDownClass()

	@property
	def storage(self):
		return self.idx_storage

	def _create_index(self, indexname):
		return self.storage.get_or_create_index(indexname=indexname, schema=sample_schema)

	def _add_2_index(self, indexname, entries=None):
		index = self._create_index(indexname=indexname)
		writer = index.writer()

		ids = list()
		entries = entries or random.randint(1, 10)
		for _ in xrange(entries):
			content = " ".join(random.sample(domain, random.randint(5, 20)))
			oid = str(uuid.uuid1())
			ids.append(oid)
			writer.add_document(id=text_type(oid), content=content)

		writer.commit()

		return (index, ids)

	def test_add_entries(self):
		idx, ids = self._add_2_index("sample1")
		with idx.searcher() as s:
			cnt = len(ids)
			self.assertEqual(cnt, s.doc_count())

			q = query.Every()
			results = s.search(q, limit=None)
			assert_that(results, has_length(cnt))

	def test_open_index(self):
		self._add_2_index("sample2")
		self.idx_storage.open_index(indexname="sample2")  # raise to fail

	def test_optimize_index(self):
		idx, _ = self._add_2_index("sample3")
		idx.optimize()  # raise to fail

	def test_search_index(self):
		index, _ = self._add_2_index("sample4", 400)
		with index.searcher() as s:
			q = query.Term("content", random.choice(domain))
			results = s.search(q, limit=None)
			assert_that(results, has_length(greater_than(0)))

	def test_delete_index(self):
		index, ids = self._add_2_index("sample5", 50)
		writer = index.writer()
		writer.delete_by_term('id', unicode(ids[0]))
		writer.commit()

		with index.searcher() as s:
			q = query.Term("id", unicode(ids[0]))
			results = s.search(q, limit=None)
			assert_that(results, has_length(0))

class TestDirectoryStorage(ConfiguringTestBase, _IndexStorageTest):

	@classmethod
	def setUpClass(cls):
		cls.indexdir = tempfile.mkdtemp(dir="/tmp")
		cls.idx_storage = DirectoryStorage(cls.indexdir)
		super(TestDirectoryStorage, cls).setUpClass()
