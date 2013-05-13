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

from whoosh.query import (Term)

from ...RenderedBook import _EclipseTOCMiniDomTopic
from .._whoosh_nti_card_indexer import _DefaultWhooshNTICardIndexer

from . import ConfiguringTestBase

from hamcrest import (assert_that, has_length, is_)

class TestNTICardIndexer(ConfiguringTestBase):

	@classmethod
	def setUpClass(cls):
		super(TestNTICardIndexer, cls).setUpClass()
		cls.idxdir = tempfile.mkdtemp(dir="/tmp")

	@classmethod
	def tearDownClass(cls):
		shutil.rmtree(cls.idxdir, True)
		super(TestNTICardIndexer, cls).tearDownClass()

	def _index_file(self, path, indexname, nodename, indexer=None):
		indexer = indexer or _DefaultWhooshNTICardIndexer()
		node = _EclipseTOCMiniDomTopic(None, path, path, None, nodename)

		idx = indexer.create_index(self.idxdir, indexname)
		writer = idx.writer(optimize=False, merge=False)
		count = indexer.process_topic(None, node, writer)
		writer.commit(optimize=False, merge=False)
		return idx, count

	def test_index_prmia(self):
		indexname = 'aopsnticard'
		path = os.path.join(os.path.dirname(__file__), 'why_start_with_arithmetic_.html')
		idx, count = self._index_file(path, indexname, 'nticardindexer')
		try:
			assert_that(count, is_(1))
			q = Term(u"content", u"divide")
			with idx.searcher() as s:
				r = s.search(q, limit=None)
				assert_that(r, has_length(1))
		finally:
			idx.close()
