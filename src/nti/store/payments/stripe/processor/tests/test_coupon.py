#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import assert_that

import time
import unittest

from nti.store.payments.stripe.processor.coupon import CouponProcessor

from nti.store.payments.stripe.processor.tests import StripeProcessorTestLayer

class TestCouponProcessor(unittest.TestCase):

	layer = StripeProcessorTestLayer

	def setUp(self):
		super(TestCouponProcessor, self).setUp()
		self.manager = CouponProcessor()

	def test_validate_coupon(self):

		class Coupon(object):
			duration = 'forever'
			redeem_by = None
			max_redemptions = None
			duration_in_months = None

		c = Coupon()
		c.duration = 'forever'
		assert_that(self.manager.validate_coupon(c), is_(True))

		c.duration = 'once'
		assert_that(self.manager.validate_coupon(c), is_(True))
		c.redeem_by = time.time() + 100000
		assert_that(self.manager.validate_coupon(c), is_(True))
		c.redeem_by = time.time() - 100000
		assert_that(self.manager.validate_coupon(c), is_(False))

		c.duration = 'repeating'
		assert_that(self.manager.validate_coupon(c), is_(False))
		c.redeem_by = time.time() + 100000
		assert_that(self.manager.validate_coupon(c), is_(True))
		c.redeem_by = None
		c.max_redemptions = 0
		assert_that(self.manager.validate_coupon(c), is_(False))
		c.max_redemptions = 1
		assert_that(self.manager.validate_coupon(c), is_(True))
		c.max_redemptions = None
		c.duration_in_months = 0
		assert_that(self.manager.validate_coupon(c), is_(False))
		c.duration_in_months = 10
		assert_that(self.manager.validate_coupon(c), is_(True))

	def test_apply_coupon(self):
		amount = 1000
		class Coupon(object):
			amount_off = None
			percent_off = None

		c = Coupon()
		c.percent_off = 0.10
		amt = self.manager.apply_coupon(amount, c)
		assert_that(amt, is_(900))

		c = Coupon()
		c.percent_off = 20.0
		amt = self.manager.apply_coupon(amount, c)
		assert_that(amt, is_(800))

		c = Coupon()
		c.amount_off = 2000
		amt = self.manager.apply_coupon(amount, c)
		assert_that(amt, is_(980))
