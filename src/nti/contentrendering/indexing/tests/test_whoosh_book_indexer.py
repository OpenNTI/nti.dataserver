#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import has_length
from hamcrest import assert_that

import os
import shutil
import tempfile

from whoosh.query import Or
from whoosh.query import Term

from ...RenderedBook import _EclipseTOCMiniDomTopic
from ..whoosh_book_indexer import _BookFileWhooshIndexer
from ..whoosh_book_indexer import _IdentifiableNodeWhooshIndexer
from ...utils import NoConcurrentPhantomRenderedBook, EmptyMockDocument

from nti.contentrendering.tests import NonDevmodeContentrenderingLayerTest

class TestWhooshBookIndexer(NonDevmodeContentrenderingLayerTest):

	#  non devmode to load the tagger

	def setUp(self):
		super(TestWhooshBookIndexer, self).setUp()
		self.idxdir = tempfile.mkdtemp(dir="/tmp")

	def tearDown(self):
		shutil.rmtree(self.idxdir, True)
		super(TestWhooshBookIndexer, self).tearDown()

	def _test_book_indexer(self, clazz, bio_expected, homeo_expected):
		indexname = 'biology'
		path = os.path.join(os.path.dirname(__file__),
							'../../tests/intro-biology-rendered-book')

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
		self._test_book_indexer(_BookFileWhooshIndexer, 8, 4)

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
