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
from .._whoosh_video_transcript_indexer import _DefaultWhooshVideoTranscriptIndexer

from . import ConfiguringTestBase

from hamcrest import (assert_that, has_length, is_)

class TestWhooshVideoTranscriptIndexer(ConfiguringTestBase):

	@classmethod
	def setUpClass(cls):
		super(TestWhooshVideoTranscriptIndexer, cls).setUpClass()
		cls.idxdir = tempfile.mkdtemp(dir="/tmp")

	@classmethod
	def tearDownClass(cls):
		shutil.rmtree(cls.idxdir, True)
		super(TestWhooshVideoTranscriptIndexer, cls).tearDownClass()

	def _index_file(self, path, indexname, nodename, indexer=None):
		indexer = indexer or _DefaultWhooshVideoTranscriptIndexer()
		node = _EclipseTOCMiniDomTopic(None, path, path, None, nodename)

		idx = indexer.create_index(self.idxdir, indexname)
		writer = idx.writer(optimize=False, merge=False)
		videos, containerId = indexer.process_topic(None, node, writer)
		count = indexer._parse_and_index_videos(videos, containerId, writer)
		writer.commit(optimize=False, merge=False)
		return idx, count

	def test_index_prmia(self):
		indexname = 'prmiavt'
		path = os.path.join(os.path.dirname(__file__), 'framework_for_diagnosing_systemic_risk.html')
		idx, count = self._index_file(path, indexname, 'videoindexer')
		try:
			assert_that(count, is_(78))
			q = Term(u"content", u"banking")
			with idx.searcher() as s:
				r = s.search(q, limit=None)
				assert_that(r, has_length(11))
		finally:
			idx.close()

	def test_index_selenium(self):
		indexname = 'selenium'
		path = os.path.join(os.path.dirname(__file__), 'selenium_unified_video.html')
		idx, count = self._index_file(path, indexname, 'videoindexer')
		try:
			assert_that(count, is_(10))
			q = Term(u"content", u"columbia")
			with idx.searcher() as s:
				r = s.search(q, limit=None)
				assert_that(r, has_length(1))
				for h in r:
					assert_that(h['containerId'], is_(u'tag:nextthought.com,2011-10:USSC-HTML-SeleniumTestContent.unified_video'))
					assert_that(h['videoId'], is_(u'tag:nextthought.com,2011-10:USSC-NTIVideo-SeleniumTestContent.ntivideo.1'))
					assert_that(h['content'], has_length(84))
					assert_that(str(h['end_timestamp']), is_('0001-01-01 00:00:22.489000'))
					assert_that(str(h['start_timestamp']), is_('0001-01-01 00:00:17.829000'))
		finally:
			idx.close()
