#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import is_not
from hamcrest import has_length
from hamcrest import assert_that

import os
import shutil
import tempfile

from whoosh.query import (Term)

from ..nticard_indexer import _DefaultWhooshNTICardIndexer

from ...RenderedBook import _EclipseTOCMiniDomTopic

from nti.contentrendering.tests import NonDevmodeContentrenderingLayerTest

class TestNTICardIndexer(NonDevmodeContentrenderingLayerTest):

	# non devmode to load the tagger


	def setUp(self):
		super(TestNTICardIndexer, self).setUp()
		self.idxdir = tempfile.mkdtemp(dir="/tmp")

	def tearDown(self):
		shutil.rmtree(self.idxdir, True)
		super(TestNTICardIndexer, self).tearDown()

	def _index_file(self, path, indexname, nodename, indexer=None):
		indexer = indexer or _DefaultWhooshNTICardIndexer()
		node = _EclipseTOCMiniDomTopic(None, path, path, None, nodename)

		idx = indexer.create_index(self.idxdir, indexname)
		writer = idx.writer(optimize=False, merge=False)
		cards = indexer.process_topic(None, node, writer)
		count = indexer._index_cards(cards, writer)
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
				for hit in r:
					assert_that(hit['type'], is_not(u''))
					assert_that(hit['href'], is_not(u''))
					assert_that(hit['title'], is_not(u''))
					assert_that(hit['content'], is_not(u''))
					assert_that(hit['creator'], is_not(u''))
					assert_that(hit['containerId'], is_not(u''))
					assert_that(hit['href'], is_("http://www.aops.org"))
					assert_that(hit['target_ntiid'], is_("tag:nextthought.com,2011-10:AOPS-HTML-prealgebra.chapter:arithmetic"))
		finally:
			idx.close()
