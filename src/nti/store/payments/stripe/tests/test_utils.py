#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import uuid
import stripe

from zope import component

from nti.store import interfaces as store_interfaces
from ..stripe_purchase import create_stripe_priceable

from . import ConfiguringTestBase

from hamcrest import (assert_that, has_length, is_not, none, is_)

class TestUtils(ConfiguringTestBase):

	@classmethod
	def setUpClass(cls):
		super(TestUtils, cls).setUpClass()
		cls.api_key = stripe.api_key
		stripe.api_key = u'sk_test_3K9VJFyfj0oGIMi7Aeg3HNBp'
		code = str(uuid.uuid4())
		cls.coupon = stripe.Coupon.create(percent_off=25, duration='once', id=code)

	@classmethod
	def tearDownClass(cls):
		super(TestUtils, cls).tearDownClass()
		cls.coupon.delete()
		stripe.api_key = cls.api_key

	def test_price(self):
		pricer = component.getUtility(store_interfaces.IPurchasablePricer, name="stripe")
		p = create_stripe_priceable(u"bleach", 5, self.coupon.id)
		priced = pricer.price(p)
		assert_that(priced, is_not(none()))
		assert_that(priced.NTIID, is_(u'bleach'))
		assert_that(priced.PurchaseFee, is_(75))
		assert_that(priced.PurchasePrice, is_(750))
		assert_that(priced.NonDiscountedPrice, is_(1000))
		assert_that(priced.Quantity, is_(5))

	def test_evaluate(self):
		pricer = component.getUtility(store_interfaces.IPurchasablePricer, name="stripe")
		p0 = create_stripe_priceable(u"bleach", 5, self.coupon.id)
		p1 = create_stripe_priceable(u"xyz-book", 1)
		result = pricer.evaluate((p0, p1))
		assert_that(result, is_not(none()))
		assert_that(result.PricedList, has_length(2))
		assert_that(result.TotalPurchaseFee, is_(95))
		assert_that(result.TotalPurchasePrice, is_(850))
		assert_that(result.TotalNonDiscountedPrice, is_(1100))
