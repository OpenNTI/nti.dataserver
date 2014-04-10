#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import assert_that
from hamcrest import has_property

import unittest

from nti.dataserver.users import User
from nti.dataserver.contenttypes import Note
from nti.dataserver.contenttypes import Highlight

from nti.ntiids.ntiids import make_ntiid

from nti.contentsearch.search_hits import get_search_hit
from nti.contentsearch import interfaces as search_interfaces
from nti.contentsearch.search_results import _SearchResults as SearchResults
from nti.contentsearch.search_comparators import _RelevanceSearchHitComparator as RSHC

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.contentsearch.tests import zanpakuto_commands
from nti.contentsearch.tests import SharedConfiguringTestLayer

class TestSearchComparators(unittest.TestCase):

	layer = SharedConfiguringTestLayer

	def _create_user(self, username='nt@nti.com', password='temp001'):
		ds = mock_dataserver.current_mock_ds
		usr = User.create_user(ds, username=username, password=password)
		return usr

	def test_relevance_path_score(self):
		path = ref = ('a', 'b', 'c', 'd')
		assert_that(RSHC.score_path(ref, path), is_(10000))
		path = ref + ('e',)
		assert_that(RSHC.score_path(ref, path), is_(9000))
		path = ('a', 'b', 'c')
		assert_that(RSHC.score_path(ref, path), is_(60))
		path = ('a', 'b')
		assert_that(RSHC.score_path(ref, path), is_(40))
		path = ('a',)
		assert_that(RSHC.score_path(ref, path), is_(20))
		path = ('a', 'b', 'c', 'x')
		assert_that(RSHC.score_path(ref, path), is_(59))
		path = ('a', 'b', 'c', 'x', 'y')
		assert_that(RSHC.score_path(ref, path), is_(58))
		path = ('a', 'b', 'x', 'y')
		assert_that(RSHC.score_path(ref, path), is_(38))
		path = ('a', 'x', 'y', 'z')
		assert_that(RSHC.score_path(ref, path), is_(17))
		path = ('x', 'y', 'z')
		assert_that(RSHC.score_path(ref, path), is_(0))
		assert_that(RSHC.score_path(ref, ()), is_(0))

	@WithMockDSTrans
	def test_search_hit_relevance(self):
		query = search_interfaces.ISearchQuery("all")
		query.location = make_ntiid(nttype='bleach', specific='manga')
		query.sortOn = 'relevance'
		result = SearchResults(query)

		# create UGD objects
		usr = self._create_user()
		for y, x  in enumerate(zanpakuto_commands):
			if  y % 2 == 0:
				ugd = Note()
				score = 2.0
				ugd.body = [unicode(x)]
			else:
				score = 1.0
				ugd = Highlight()
				ugd.selectedText = unicode(x)
			ugd.creator = usr.username
			ugd.containerId = make_ntiid(nttype='bleach', specific='manga%s' % y)
			mock_dataserver.current_transaction.add(ugd)
			ugd = usr.addContainedObject(ugd)

			hit = get_search_hit(ugd, score, query)
			result.add(hit, score)

		# sort
		result.sort()
		# check
		for n, hit in enumerate(result.Hits):
			if (n + 1) <= len(zanpakuto_commands) / 2:
				assert_that(hit, has_property('Type', is_('Note')))
			else:
				assert_that(hit, has_property('Type', is_('Highlight')))

