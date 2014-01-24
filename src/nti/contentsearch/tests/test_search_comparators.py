#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import has_length
from hamcrest import assert_that

from nti.dataserver.users import User
from nti.dataserver.contenttypes import Note
from nti.dataserver.contenttypes import Highlight

from nti.ntiids.ntiids import make_ntiid

from nti.externalization.externalization import toExternalObject

from .. import interfaces as search_interfaces
from ..search_comparators import _RelevanceSearchHitComparator as RSHC

from ..constants import (ITEMS, TYPE)

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from . import zanpakuto_commands
from . import ConfiguringTestBase

class TestSearchComparators(ConfiguringTestBase):

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
		usr = self._create_user()
		rim = search_interfaces.IRepozeEntityIndexManager(usr)
		for x in zanpakuto_commands:
			for n in xrange(2):
				if  n == 0:
					ugd = Note()
					ugd.body = [unicode(x)]
				else:
					ugd = Highlight()
					ugd.selectedText = unicode(x)
				ugd.creator = usr.username
				ugd.containerId = make_ntiid(nttype='bleach', specific='manga%s' % n)
				mock_dataserver.current_transaction.add(ugd)
				ugd = usr.addContainedObject(ugd)
				rim.index_content(ugd)

		query = search_interfaces.ISearchQuery("all")
		query.location = make_ntiid(nttype='bleach', specific='manga')
		query.sortOn = 'relevance'
		hits = rim.search(query)
		assert_that(hits, has_length(6))
		hits = toExternalObject(hits)
		items = hits[ITEMS]
		for n, hit in enumerate(items):
			if n <= 2:
				assert_that(hit[TYPE], is_('Note'))
			else:
				assert_that(hit[TYPE], is_('Highlight'))
