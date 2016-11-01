#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import has_length
from hamcrest import assert_that

import time
import shutil
import tempfile
import unittest
from datetime import datetime

from nti.ntiids.ntiids import make_ntiid


from nti.contentsearch.search_query import QueryObject

from nti.contentsearch.indexmanager import create_index_manager
from nti.contentsearch.whoosh_schemas import create_book_schema
from nti.contentsearch.whoosh_storage import create_directory_index
from nti.contentsearch.whoosh_searcher import WhooshContentSearcher

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from . import phrases
from . import find_test
from . import SharedConfiguringTestLayer

from nti.testing.matchers import is_false
from nti.testing.matchers import is_true

class IndexManagerTestLayer(SharedConfiguringTestLayer):

	@classmethod
	def _add_book_data(cls):
		indexname = 'bleach'
		cls.now = time.time()
		cls.book_idx_dir = tempfile.mkdtemp()
		_, storage = create_directory_index(indexname, create_book_schema(),
											cls.book_idx_dir)
		cls.bim = WhooshContentSearcher(indexname, storage)

		writer = cls.bim.get_index(indexname).writer()
		for k, x in enumerate(phrases):
			writer.add_document(ntiid=unicode(make_ntiid(provider=str(k),
											  nttype='bleach', specific='manga')),
								title=unicode(x),
								content=unicode(x),
								quick=unicode(x),
								related=u'',
								last_modified=datetime.fromtimestamp(cls.now))
		writer.commit()

	@classmethod
	def setUp(cls):
		cls._add_book_data()

	@classmethod
	def testSetUp(cls, test=None):
		test = test or find_test()

		test.now = cls.now
		test.bim = cls.bim
		test.book_idx_dir = cls.book_idx_dir
		test.im = create_index_manager()

	@classmethod
	def tearDown(cls):
		cls.bim.close()
		shutil.rmtree(cls.book_idx_dir, True)

	@classmethod
	def testTearDown(cls):
		pass

class TestIndexManager(unittest.TestCase):

	layer = IndexManagerTestLayer

	now = None
	bim = None
	book_idx_dir = None
	im = None


	@WithMockDSTrans
	def test_register_content(self):
		assert_that(self.im.register_content(indexname='unknown', ntiid='unknown',
											 indexdir=self.book_idx_dir),
					is_false())

		assert_that(self.im.register_content(indexname='bleach', ntiid='bleach', indexdir=self.book_idx_dir),
					is_true())

		assert_that( self.im.unregister_content('bleach'),
					 is_true() )

		assert_that( self.im.unregister_content('bleach'),
					 is_false() )


	@WithMockDSTrans
	def test_search_book(self):
		self.im.register_content(indexname='bleach', ntiid='bleach', indexdir=self.book_idx_dir)

		q = QueryObject(indexid='bleach', term='omega')
		hits = self.im.content_search(query=q)
		assert_that(hits, has_length(1))

		q = QueryObject(indexid='bleach', term='extre')
		hits = self.im.content_suggest(query=q)
		assert_that(hits, has_length(1))


	@WithMockDSTrans
	def test_unified_search_suggest(self):
		self.im.register_content(indexname='bleach', ntiid='bleach', indexdir=self.book_idx_dir)

		q = QueryObject(term='omeg', indexid='bleach')
		hits = self.im.suggest(q)
		assert_that(hits, has_length(1))
