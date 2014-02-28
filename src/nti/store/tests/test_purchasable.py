#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import is_in
from hamcrest import is_not
from hamcrest import has_key
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import greater_than_or_equal_to

import unittest

from zope import component

from nti.dataserver.users import User

from nti.store import purchasable
from nti.store import purchase_order
from nti.store import purchase_attempt
from nti.store import interfaces as store_interfaces

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.store.tests import SharedConfiguringTestLayer

class TestPurchasable(unittest.TestCase):

	layer = SharedConfiguringTestLayer

	processor = 'stripe'

	def _create_user(self, username='nt@nti.com', password='temp001'):
		usr = User.create_user(self.ds, username=username, password=password)
		return usr

	def test_zmcl(self):
		util = component.queryUtility(store_interfaces.IPurchasableStore)
		assert_that(util, is_not(none()))
		assert_that(util, has_length(greater_than_or_equal_to(4)))

		assert_that(util.get_purchasable('iid_0'), is_not(none()))

		ps = util.get_purchasable('iid_3')
		assert_that(ps.NTIID, is_("iid_3"))
		assert_that(ps.Title, is_("Risk Course"))
		assert_that(ps.Description, is_("Intro to Risk"))
		assert_that(ps.Provider, is_("PRMIA"))
		assert_that(ps.Amount, is_(90))
		assert_that(ps.Currency, is_("USD"))
		assert_that(ps.Discountable, is_(True))
		assert_that(ps.BulkPurchase, is_(False))
		assert_that(ps.Items, has_length(2))
		assert_that(ps.License, "1 Year License")

	@WithMockDSTrans
	def test_available(self):
		self._create_user()
		m = purchasable.get_available_items('nt@nti.com')
		assert_that(m, has_key('iid_1'))
		assert_that(m, has_key('iid_2'))

	def _create_purchase_attempt(self, item=u'iid_3', quantity=None,
								 state=store_interfaces.PA_STATE_UNKNOWN):
		pi = purchase_order.create_purchase_item(item, 1)
		po = purchase_order.create_purchase_order(pi, quantity=quantity)
		pa = purchase_attempt.create_purchase_attempt(po, processor=self.processor,
													  state=state)
		return pa

	@WithMockDSTrans
	def test_purchased(self):
		user = self._create_user()
		hist = store_interfaces.IPurchaseHistory(user, None)
		pa = self._create_purchase_attempt(u'iid_3',
											state=store_interfaces.PA_STATE_SUCCESS)
		hist.add_purchase(pa)

		m = purchasable.get_available_items('nt@nti.com')
		assert_that(m, is_not(has_key('iid_3')))

	def test_get_content_items(self):
		items = purchasable.get_content_items("iid_3")
		assert_that(items, has_length(2))
		assert_that('var-risk', is_in(items))
		assert_that('volatility', is_in(items))
