#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import is_not
from hamcrest import has_key
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import contains_inanyorder

import time
import shutil
import tempfile
import unittest
from datetime import datetime

from nti.ntiids.ntiids import make_ntiid

from nti.externalization.externalization import toExternalObject

from nti.contentindexing.whooshidx.schemas import create_book_schema
from nti.contentindexing.whooshidx.schemas import create_nti_card_schema
from nti.contentindexing.whooshidx.schemas import create_video_transcript_schema

from nti.contentsearch import constants
from nti.contentsearch.common import videotimestamp_to_datetime
from nti.contentsearch.whoosh_searcher import WhooshContentSearcher
from nti.contentsearch.whoosh_storage import create_directory_index
from nti.contentsearch.constants import (HIT, HIT_COUNT, ITEMS, SUGGESTIONS)

from nti.contentsearch.tests import find_test
from nti.contentsearch.tests import zanpakuto_commands
from nti.contentsearch.tests import SharedConfiguringTestLayer

episodes = ((u'e365', u'Secret of the Substitute Badge'),
			(u'e007', u'Greetings from a Stuffed Toy'))

nticards = ((u'c001', u'Xcution attacks Ginjo'),
			(u'c002', u'Fullbring, The Detested Power'))

def setUpIndexes(test):
	test.now = time.time()
	baseindexname = 'bleach'
	test.idx_dir = tempfile.mkdtemp(dir="/tmp")

	# create file schemas
	factories = (('', create_book_schema),
				 (constants.vtrans_prefix, create_video_transcript_schema),
				 (constants.nticard_prefix, create_nti_card_schema))

	for postfix, func in factories:
		indexname = postfix + baseindexname
		_ , test.storage = create_directory_index(indexname, func(), test.idx_dir)

	# create content manager
	test.bim = WhooshContentSearcher(baseindexname, storage=test.storage)

	# add book entries
	writer = test.bim.get_index(baseindexname).writer()
	for k, x in enumerate(zanpakuto_commands):
		writer.add_document(ntiid=unicode(make_ntiid(provider=str(k),
													 nttype='bleach',
													 specific='manga')),
							title=unicode(x),
							content=unicode(x),
							quick=unicode(x),
							related=u'',
							last_modified=datetime.fromtimestamp(test.now))
	writer.commit()

	# add video entries
	writer = test.bim.get_index('vtrans_%s' % baseindexname).writer()
	for e, x in episodes:
		writer.add_document(containerId=unicode(make_ntiid(provider='tite_kubo',
														   nttype='bleach',
														   specific='manga')),
							videoId=unicode(make_ntiid(provider='bleachget',
													   nttype='bleach',
													   specific=e)),
							content=x,
							quick=x,
							title=unicode(e),
							start_timestamp=videotimestamp_to_datetime(u'00:00:01,630'),
							end_timestamp=videotimestamp_to_datetime('00:00:22,780'),
							last_modified=datetime.fromtimestamp(test.now))
	writer.commit()

	# add nticard entries
	writer = test.bim.get_index('nticard_%s' % baseindexname).writer()
	for e, x in nticards:
		writer.add_document(containerId=unicode(make_ntiid(provider='tite_kubo',
														   nttype='bleach',
														   specific='manga')),
							ntiid=unicode(make_ntiid(provider='bleachget',
													 nttype='bleach',
													 specific=e)),
							type=u'summary',
							content=x,
							quick=x,
							title=e,
							creator=u'tite kubo',
							href=u'http://www.bleachget.com',
							target_ntiid=unicode(make_ntiid(provider='tite_kubo',
														    nttype='bleach',
														    specific='episodes')),
							last_modified=datetime.fromtimestamp(test.now))
	writer.commit()
	
class WhooshContentSearcherTestLayer(SharedConfiguringTestLayer):

	@classmethod
	def setUp(cls):
		setUpIndexes(cls)

	@classmethod
	def testSetUp(cls, test=None):
		cls.test = test or find_test()
		cls.test.bim = cls.bim
		cls.test.idx_dir = cls.idx_dir
		cls.test.storage = cls.storage

	@classmethod
	def tearDown(cls):
		cls.bim.close()
		shutil.rmtree(cls.idx_dir, True)

class TestWhooshContentSearcher(unittest.TestCase):

	layer = WhooshContentSearcherTestLayer

	def test_search(self):
		hits = toExternalObject(self.bim.search('shield'))
		assert_that(hits, has_entry(HIT_COUNT, 1))
		assert_that(hits, has_entry('Query', 'shield'))
		assert_that(hits, has_key(ITEMS))

		items = hits[ITEMS]
		assert_that(items, has_length(1))

		item = items[0]
		assert_that(item, has_entry('Class', HIT))
		assert_that(item, has_entry('NTIID', is_not(None)))
		assert_that(item, has_entry('Score', is_not(None)))
		assert_that(item, has_entry('ContainerId', is_not(None)))
		assert_that(item,
					has_entry(
						'Snippet',
						'All Waves, Rise now and Become my Shield, Lightning, Strike now and Become my Blade'))

	def test_search_video(self):
		hits = toExternalObject(self.bim.search("secret"))
		assert_that(hits, has_entry(HIT_COUNT, 1))
		assert_that(hits, has_entry('Query', 'secret'))
		assert_that(hits, has_key(ITEMS))
		items = hits[ITEMS]
		assert_that(items, has_length(1))
		assert_that(items[0], has_entry('Class', HIT))
		assert_that(items[0], has_entry('NTIID', is_not(None)))
		assert_that(items[0], has_entry('Score', is_not(None)))
		assert_that(items[0], has_entry('VideoID', is_not(None)))
		assert_that(items[0], has_entry('ContainerId', is_not(None)))
		assert_that(items[0], has_entry('Snippet', 'Secret of the Substitute Badge'))
		assert_that(items[0], has_entry('StartMilliSecs', 1630.0))
		assert_that(items[0], has_entry('EndMilliSecs', 22780.0))

	def test_search_nticard(self):
		hits = toExternalObject(self.bim.search('Xcution'))
		assert_that(hits, has_entry(HIT_COUNT, 1))
		assert_that(hits, has_entry('Query', 'Xcution'))
		assert_that(hits, has_key(ITEMS))
		items = hits[ITEMS]
		assert_that(items, has_length(1))
		assert_that(items[0], has_entry('Class', HIT))
		assert_that(items[0], has_entry('NTIID', is_not(None)))
		assert_that(items[0], has_entry('Score', is_not(None)))
		assert_that(items[0], has_entry('ContainerId', is_not(None)))
		assert_that(items[0], has_entry('Snippet', 'Xcution attacks Ginjo'))
		assert_that(items[0], has_entry('Title', is_not(None)))
		assert_that(items[0], has_entry('Href', 'http://www.bleachget.com'))
		assert_that(items[0], has_entry('TargetNTIID', is_not(None)))

	def test_longword_search(self):
		hits = toExternalObject(self.bim.search("multiplication"))
		assert_that(hits, has_entry(HIT_COUNT, 1))
		assert_that(hits, has_entry('Query', 'multiplication'))
		assert_that(hits, has_key(ITEMS))

		items = hits[ITEMS]
		item = items[0]
		assert_that(item,
			has_entry('Snippet',
					 'Multiplication and subtraction of fire and ice, show your might'))

	def test_search_start(self):
		hits = toExternalObject(self.bim.search("ra*"))
		assert_that(hits, has_entry(HIT_COUNT, 3))
		assert_that(hits, has_entry('Query', 'ra*'))
		assert_that(hits, has_key(ITEMS))
		items = hits[ITEMS]
		assert_that(items, has_length(3))
		for item in items:
			assert_that(item, has_entry('Score', is_(2.0)))

	def test_partial_search_start(self):
		hits = toExternalObject(self.bim.search("bl"))
		items = hits[ITEMS]
		assert_that(items, has_length(2))
		for item in items:
			assert_that(item, has_entry('Score', is_not(None)))

	def test_suggest(self):
		hits = toExternalObject(self.bim.suggest("ra"))
		assert_that(hits, has_entry(HIT_COUNT, 4))
		assert_that(hits, has_entry('Query', 'ra'))
		assert_that(hits, has_key(ITEMS))

		items = hits[ITEMS]
		assert_that(items, has_length(4))
		assert_that(items, contains_inanyorder('rage', 'rankle', 'rain', 'raise'))

	def test_suggest_and_search(self):
		hits = toExternalObject(self.bim.suggest_and_search("ra"))
		assert_that(hits, has_entry(HIT_COUNT, 1))
		assert_that(hits, has_entry('Query', u'ra'))
		assert_that(hits, has_key(ITEMS))
		assert_that(hits[ITEMS], has_length(1))
		assert_that(hits[SUGGESTIONS], has_length(4))
