#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from nti.store.payments.stripe import stripe_purchase

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from . import ConfiguringTestBase

from hamcrest import (assert_that, is_, is_not, has_length, none)

class TestStripePurchase(ConfiguringTestBase):

	book_id = 'xyz-book'

	def _create_purchase_order(self, item, quantity=None, coupon=None):
		pi = stripe_purchase.create_stripe_purchase_item(item, 1)
		po = stripe_purchase.create_stripe_purchase_order(pi, quantity=quantity, coupon=coupon)
		return po

	@WithMockDSTrans
	def test_copy_purchase_order(self):
		po = self._create_purchase_order(self.book_id, quantity=2, coupon='mycoupon')
		cp = po.copy()
		assert_that(cp, is_not(none()))
		assert_that(id(po), is_not(id(cp)))
		# check items
		assert_that(cp.Items, has_length(1))
		assert_that(cp.Items[0].NTIID, is_(self.book_id))
		assert_that(cp.Items[0].Quantity, is_(2))
		# check order
		assert_that(cp.Coupon, is_('mycoupon'))
		assert_that(cp.Quantity, is_(2))


