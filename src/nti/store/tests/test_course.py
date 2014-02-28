#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import has_key
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_property
from hamcrest import greater_than_or_equal_to

import unittest

from zope import component

from nti.dataserver.users import User

from nti.store import purchasable
from nti.store import interfaces as store_interfaces

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.store.tests import SharedConfiguringTestLayer

class TestCourse(unittest.TestCase):

	layer = SharedConfiguringTestLayer

	def _create_user(self, username='nt@nti.com', password='temp001'):
		usr = User.create_user(self.ds, username=username, password=password)
		return usr

	def test_zmcl(self):
		util = component.queryUtility(store_interfaces.IPurchasableStore)
		assert_that(util, is_not(none()))
		assert_that(util, has_length(greater_than_or_equal_to(1)))

		assert_that(util.get_purchasable('tag:nextthought.com,2011-10:OU-course-CLC3403LawAndJustice'), is_not(none()))

		ps = util.get_purchasable('tag:nextthought.com,2011-10:OU-course-CLC3403LawAndJustice')
		assert_that(ps, has_property('NTIID', "tag:nextthought.com,2011-10:OU-course-CLC3403LawAndJustice"))
		assert_that(ps, has_property('Title', "CLC 3403 Law and Justice"))
		assert_that(ps, has_property('Description', has_length(greater_than_or_equal_to(140))))
		assert_that(ps, has_property('Amount', is_(none())))
		assert_that(ps, has_property('Currency', is_(none())))
		assert_that(ps, has_property('Discountable', is_(False)))
		assert_that(ps, has_property('BulkPurchase', is_(False)))
		assert_that(ps, has_property('Featured', is_(True)))
		assert_that(ps, has_property('Preview', is_(True)))
		assert_that(ps, has_property('Items', has_length(1)))
		assert_that(ps, has_property('License', is_(none())))
		assert_that(ps, has_property('Name', is_('CLC 3403')))
		assert_that(ps, has_property('Icon', is_('http://www.ou.edu/icon.gif')))
		assert_that(ps, has_property('Thumbnail', is_('http://www.ou.edu/thumbnail.gif')))
		assert_that(ps, has_property('Communities', has_length(1)))
		assert_that(ps, has_property('Department', 'Law'))
		assert_that(ps, has_property('StartDate', '2013-05-11'))

	@WithMockDSTrans
	def test_available(self):
		self._create_user()
		m = purchasable.get_available_items('nt@nti.com')
		assert_that(m, has_key('tag:nextthought.com,2011-10:OU-course-CLC3403LawAndJustice'))

