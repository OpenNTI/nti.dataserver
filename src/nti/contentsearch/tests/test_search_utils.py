#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import unittest

from hamcrest import is_
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_property
from hamcrest import greater_than_or_equal_to

from nti.ntiids.ntiids import make_ntiid

from nti.contentsearch import interfaces as search_interfaces

from nti.contentsearch.search_utils import create_queryobject

from nti.contentsearch.tests import SharedConfiguringTestLayer

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

class TestSearchUtils(unittest.TestCase):

	layer = SharedConfiguringTestLayer

	@WithMockDSTrans
	def test_create_query_object_accept(self):
		ntiid = make_ntiid(nttype='hollow', specific='vastolorde')
		params = {'accept':'application/vnd.nextthought.forums.personalblogentrypost,application/vnd.nextthought.note',
				  'batchSize':10, 'batchStart':0, 'term':'menos', 'ntiid':ntiid}

		qo = create_queryobject('harribel@bleach.com', params)
		assert_that(search_interfaces.ISearchQuery.providedBy(qo), is_(True))
		assert_that(qo.username, is_('harribel@bleach.com'))
		assert_that(qo.term, is_('menos'))
		assert_that(qo.location, is_(ntiid))
		assert_that(qo.batchSize, is_(10))
		assert_that(qo.batchStart, is_(0))
		assert_that(sorted(qo.searchOn), is_(sorted((u'note', u'post'))))

	@WithMockDSTrans
	def test_create_query_object_exclude(self):
		ntiid = make_ntiid(nttype='hollow', specific='vastolorde')
		params = {'exclude':'application/vnd.nextthought.forums.personalblogentrypost,application/vnd.nextthought.note',
				  'batchSize':100, 'batchStart':3, 'term':'arrancar', 'ntiid':ntiid}

		qo = create_queryobject('ulquiorra@bleach.com', params)
		assert_that(search_interfaces.ISearchQuery.providedBy(qo), is_(True))
		assert_that(qo.username, is_('ulquiorra@bleach.com'))
		assert_that(qo.term, is_('arrancar'))
		assert_that(qo.location, is_(ntiid))
		assert_that(qo.batchSize, is_(100))
		assert_that(qo.batchStart, is_(3))
		assert_that(qo.searchOn, has_length(greater_than_or_equal_to(7)))

	@WithMockDSTrans
	def test_create_query_object_badnumbers(self):

		ntiid = make_ntiid(nttype='hollow', specific='vastolorde')
		params = {'batchSize':-100, 'batchStart':3,
				  'term':'arrancar', 'ntiid':ntiid}

		try:
			create_queryobject('ulquiorra@bleach.com', params)
			self.fail()
		except:
			pass

		params = {'batchSize':100, 'batchStart':-3}
		try:
			create_queryobject('ulquiorra@bleach.com', params)
			self.fail()
		except:
			pass

		params = {'batchSize':'xx', 'batchStart':-3}
		try:
			create_queryobject('ulquiorra@bleach.com', params)
			self.fail()
		except:
			pass

	@WithMockDSTrans
	def test_query_pac(self):
		ntiid = make_ntiid(nttype='hollow', specific='vastolorde')
		params = {'exclude':'application/vnd.nextthought.redaction',
				  'accept':	'application/vnd.nextthought.bookcontent,application/vnd.nextthought.highlight,' + \
				  			'application/vnd.nextthought.note,application/vnd.nextthought.forums.personalblogentrypost,' + \
				  			'application/vnd.nextthought.forums.personalblogcomment,application/vnd.nextthought.messageinfo',
				  'sortOn': 'relevance',
				  'sortOrder' : 'descending',
				  'batchSize':78, 'batchStart':5,
				  'term':'arrancar', 'ntiid':ntiid}
		qo = create_queryobject('ulquiorra@bleach.com', params)
		assert_that(qo.username, is_('ulquiorra@bleach.com'))
		assert_that(qo.term, is_('arrancar'))
		assert_that(qo.location, is_(ntiid))
		assert_that(qo.batchSize, is_(78))
		assert_that(qo.batchStart, is_(5))
		assert_that(qo.sortOn, 'relevance')
		assert_that(qo.sortOrder, 'descending')
		assert_that(qo.searchOn, has_length(greater_than_or_equal_to(5)))
		
	@WithMockDSTrans
	def test_query_times(self):
		ntiid = make_ntiid(nttype='hollow', specific='vastolorde')		
		params = {'createdAfter': 100,
				  'createdBefore': 125.5,
				  'modifiedAfter':101,
				  'modifiedBefore': 135.5,
				  'term':'arrancar', 'ntiid':ntiid}
		qo = create_queryobject('ulquiorra@bleach.com', params)
		assert_that(qo, has_property('creationTime', has_property('startTime', is_(100))))
		assert_that(qo, has_property('creationTime', has_property('endTime', is_(125.5))))
		assert_that(qo, has_property('modificationTime', has_property('startTime', is_(101))))
		assert_that(qo, has_property('modificationTime', has_property('endTime', is_(135.5))))
