#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import time
import shutil
import tempfile
from datetime import datetime

from nti.ntiids.ntiids import make_ntiid

from nti.externalization.externalization import toExternalObject

from .._whoosh_schemas import create_book_schema
from .._whoosh_indexstorage import create_directory_index
from .._whoosh_book_searcher import WhooshBookContentSearcher

from ..constants import (HIT, CLASS, CONTAINER_ID, HIT_COUNT, QUERY, ITEMS,
									 	 SNIPPET, NTIID, SUGGESTIONS, SCORE)

from . import zanpakuto_commands
from . import ConfiguringTestBase

from hamcrest import (assert_that, has_key, has_entry, has_length, is_not, is_, contains_inanyorder)

class TestWhooshBookContentSearcher(ConfiguringTestBase):

	@classmethod
	def setUpClass(cls):
		super(TestWhooshBookContentSearcher, cls).setUpClass()
		cls.now = time.time()
		indexname = 'bleach'
		cls.idx_dir = tempfile.mkdtemp(dir="/tmp")
		_ , cls.storage = create_directory_index(indexname, create_book_schema(), cls.idx_dir)
		cls.bim = WhooshBookContentSearcher(indexname, storage=cls.storage)

		writer = cls.bim.get_index(indexname).writer()
		for k, x in enumerate(zanpakuto_commands):
			writer.add_document(ntiid=unicode(make_ntiid(provider=str(k), nttype='bleach', specific='manga')),
								title=unicode(x),
								content=unicode(x),
								quick=unicode(x),
								related=u'',
								last_modified=datetime.fromtimestamp(cls.now))
		writer.commit()

	@classmethod
	def tearDownClass(cls):
		cls.bim.close()
		shutil.rmtree(cls.idx_dir, True)
		super(TestWhooshBookContentSearcher, cls).tearDownClass()

	def test_search(self):
		hits = toExternalObject(self.bim.search("shield"))
		assert_that(hits, has_entry(HIT_COUNT, 1))
		assert_that(hits, has_entry(QUERY, 'shield'))
		assert_that(hits, has_key(ITEMS))

		items = hits[ITEMS]
		assert_that(items, has_length(1))

		item = items[0]
		assert_that(item, has_entry(CLASS, HIT))
		assert_that(item, has_entry(NTIID, is_not(None)))
		assert_that(item, has_entry(SCORE, is_not(None)))
		assert_that(item, has_entry(CONTAINER_ID, is_not(None)))
		assert_that(item, has_entry(SNIPPET, 'All Waves, Rise now and Become my Shield, Lightning, Strike now and Become my Blade'))

	def test_longword_search(self):
		hits = toExternalObject(self.bim.search("multiplication"))
		assert_that(hits, has_entry(HIT_COUNT, 1))
		assert_that(hits, has_entry(QUERY, 'multiplication'))
		assert_that(hits, has_key(ITEMS))

		items = hits[ITEMS]
		item = items[0]
		assert_that(item, has_entry(SNIPPET, 'Multiplication and subtraction of fire and ice, show your might'))

	def test_search_start(self):
		hits = toExternalObject(self.bim.search("ra*"))
		assert_that(hits, has_entry(HIT_COUNT, 3))
		assert_that(hits, has_entry(QUERY, 'ra*'))
		assert_that(hits, has_key(ITEMS))
		items = hits[ITEMS]
		assert_that(items, has_length(3))
		for item in items:
			assert_that(item, has_entry(SCORE, is_(1.0)))

	def test_partial_search_start(self):
		hits = toExternalObject(self.bim.search("bl"))
		items = hits[ITEMS]
		assert_that(items, has_length(2))
		for item in items:
			assert_that(item, has_entry(SCORE, is_not(None)))

	def test_suggest(self):
		hits = toExternalObject(self.bim.suggest("ra"))
		assert_that(hits, has_entry(HIT_COUNT, 4))
		assert_that(hits, has_entry(QUERY, 'ra'))
		assert_that(hits, has_key(ITEMS))

		items = hits[ITEMS]
		assert_that(items, has_length(4))
		assert_that(items, contains_inanyorder('rage', 'rankle', 'rain', 'raise'))


	def test_suggest_and_search(self):
		hits = toExternalObject(self.bim.suggest_and_search("ra"))
		assert_that(hits, has_entry(HIT_COUNT, 1))
		assert_that(hits, has_entry(QUERY, u'ra'))
		assert_that(hits, has_key(ITEMS))
		assert_that(hits[ITEMS], has_length(1))
		assert_that(hits[SUGGESTIONS], has_length(4))
