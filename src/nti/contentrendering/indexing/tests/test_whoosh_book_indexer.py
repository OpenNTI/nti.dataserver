#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import os
import shutil
import tempfile

from whoosh.query import (Or, Term)

from ...RenderedBook import _EclipseTOCMiniDomTopic
from .._whoosh_book_indexer import _BookFileWhooshIndexer
from .._whoosh_book_indexer import _IdentifiableNodeWhooshIndexer
from ...utils import NoConcurrentPhantomRenderedBook, EmptyMockDocument

from . import ConfiguringTestBase

from hamcrest import assert_that, has_length

class TestWhooshBookIndexer(ConfiguringTestBase):

	features = ()  # to load the tagger

	@classmethod
	def setUpClass(cls):
		super(TestWhooshBookIndexer, cls).setUpClass()
		cls.idxdir = tempfile.mkdtemp(dir="/tmp")

	@classmethod
	def tearDownClass(cls):
		shutil.rmtree(cls.idxdir, True)
		super(TestWhooshBookIndexer, cls).tearDownClass()

	def _test_book_indexer(self, clazz, bio_expected, homeo_expected):
		indexname = 'biology'
		path = os.path.join(os.path.dirname(__file__), '../../tests/intro-biology-rendered-book')

		document = EmptyMockDocument()
		document.userdata['jobname'] = indexname
		book = NoConcurrentPhantomRenderedBook(document, path)

		indexer = clazz()
		idx, _ = indexer.index(book, self.idxdir, optimize=False)

		q = Term("keywords", u"mathcounts")
		with idx.searcher() as s:
			r = s.search(q, limit=None)
			assert_that(r, has_length(0))

		q = Or([Term("content", u'biology'), ])
		with idx.searcher() as s:
			r = s.search(q, limit=None)
			assert_that(r, has_length(bio_expected))

		q = Or([Term("content", u'homeostasis'), ])
		with idx.searcher() as s:
			r = s.search(q, limit=None)
			assert_that(r, has_length(homeo_expected))

		idx.close()

	def test_identifiable_node_indexer(self):
		self._test_book_indexer(_IdentifiableNodeWhooshIndexer, 26, 16)

	def test_bookfile_indexer(self):
		self._test_book_indexer(_BookFileWhooshIndexer, 7, 4)

	def _index_file(self, path, indexname, nodename, indexer=None):
		indexer = indexer or _BookFileWhooshIndexer()
		idx = indexer.create_index(self.idxdir, indexname)
		writer = idx.writer(optimize=False, merge=False)
		node = _EclipseTOCMiniDomTopic(None, path, path, None, nodename)
		indexer.process_topic(None, node, writer)
		writer.commit(optimize=False, merge=False)
		return idx

	def test_index_prealgebra(self):
		indexname = 'prealgebra'
		path = os.path.join(os.path.dirname(__file__), 'why_start_with_arithmetic_.html')
		idx = self._index_file(path, indexname, 'why start with arithmetic')
		try:
			q = Term("content", u"exotic")
			with idx.searcher() as s:
				r = s.search(q)
				assert_that(r, has_length(1))
		finally:
			idx.close()

	def test_index_cohen(self):
		indexname = 'cohen'
		indexer = _BookFileWhooshIndexer()
		path = os.path.join(os.path.dirname(__file__), 'cohen_vs_california.html')
		idx = self._index_file(path, indexname, 'cohen vs california', indexer)
		try:
			q = Term("content", u"court's")
			with idx.searcher() as s:
				r = s.search(q)
				assert_that(r, has_length(1))
		finally:
			idx.close()
