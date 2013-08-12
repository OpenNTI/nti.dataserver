#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from zope import component

from nti.dataserver.users import User

import nti.store as store
import nti.dataserver as dataserver

from .. import purchasable
from .. import interfaces as store_interfaces

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from . import ConfiguringTestBase

from hamcrest import (assert_that, has_key, has_length, is_not, none, is_, greater_than_or_equal_to)

class TestCourse(ConfiguringTestBase):

	set_up_packages = (dataserver, store) + (('courses.zcml', 'nti.store.tests'),)

	def _create_user(self, username='nt@nti.com', password='temp001'):
		usr = User.create_user(self.ds, username=username, password=password)
		return usr

	def test_zmcl(self):
		util = component.queryUtility(store_interfaces.IPurchasableStore)
		assert_that(util, is_not(none()))
		assert_that(util, has_length(greater_than_or_equal_to(1)))

		assert_that(util.get_purchasable('tag:nextthought.com,2011-10:OU-course-CLC3403LawAndJustice'), is_not(none()))

		ps = util.get_purchasable('tag:nextthought.com,2011-10:OU-course-CLC3403LawAndJustice')
		assert_that(ps.NTIID, "tag:nextthought.com,2011-10:OU-course-CLC3403LawAndJustice")
		assert_that(ps.Title, "CLC 3403 Law and Justice")
		assert_that(ps.Description, has_length(greater_than_or_equal_to(140)))
		assert_that(ps.Amount, is_(none()))
		assert_that(ps.Currency, is_(none()))
		assert_that(ps.Discountable, is_(False))
		assert_that(ps.BulkPurchase, is_(False))
		assert_that(ps.Featured, is_(True))
		assert_that(ps.Items, has_length(1))
		assert_that(ps.License, is_(none()))
		assert_that(ps.Name, is_('CLC 3403'))
		assert_that(ps.Icon, is_('http://www.ou.edu/icon.gif'))
		assert_that(ps.Thumbnail, is_('http://www.ou.edu/thumbnail.gif'))
		assert_that(ps.Communities, has_length(1))

	@WithMockDSTrans
	def test_available(self):
		self._create_user()
		m = purchasable.get_available_items('nt@nti.com')
		assert_that(m, has_key('tag:nextthought.com,2011-10:OU-course-CLC3403LawAndJustice'))

