#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import none
from hamcrest import is_not
from hamcrest import has_key
from hamcrest import has_entry
from hamcrest import assert_that

import uuid
import stripe
import unittest

from nti.externalization.externalization import toExternalObject

from .. import StripePurchaseError
from ..stripe_purchase import create_stripe_priceable, StripePricedPurchasable

from . import SharedConfiguringTestLayer

class TestExternal(unittest.TestCase):

	layer = SharedConfiguringTestLayer

	def setUp(self):
		super(TestExternal, self).setUp()
		self.api_key = stripe.api_key
		stripe.api_key = u'sk_test_3K9VJFyfj0oGIMi7Aeg3HNBp'

	def tearDown(self):
		super(TestExternal, self).tearDown()
		stripe.api_key = self.api_key

	def test_stripe_coupon(self):
		code = str(uuid.uuid4())
		c = stripe.Coupon.create(percent_off=25, duration='once', id=code)
		ext = toExternalObject(c)
		assert_that(ext, is_not(none()))
		assert_that(ext, has_entry('ID', code))
		assert_that(ext, has_entry('Duration', 'once'))
		assert_that(ext, has_entry('PercentOff', 25))
		c.delete()

	def test_purchase_error(self):
		spe = StripePurchaseError(Type=u"Error", Message=u"My message",
								  Code=u"My code", Param=u"My param")
		ext = toExternalObject(spe)
		assert_that(ext, is_not(none()))
		assert_that(ext, has_entry('Type', 'Error'))
		assert_that(ext, has_entry('Message', 'My message'))
		assert_that(ext, has_entry('Code', "My code"))
		assert_that(ext, has_entry('Param', "My param"))

	def test_stripe_priceable(self):
		p = create_stripe_priceable("bleach", 10, 'mycoupon')
		ext = toExternalObject(p)
		assert_that(ext, is_not(none()))
		assert_that(ext, has_entry('NTIID', 'bleach'))
		assert_that(ext, has_entry('Quantity', 10))
		assert_that(ext, has_entry('Coupon', "mycoupon"))

	def test_stripe_priced_purchasable(self):
		p = StripePricedPurchasable(NTIID="bleach", Quantity=10, Coupon='mycoupon',
									PurchaseFee=5.0, PurchasePrice=100.0,
									NonDiscountedPrice=105.0)
		ext = toExternalObject(p)
		assert_that(ext, is_not(none()))
		assert_that(ext, has_entry('NTIID', 'bleach'))
		assert_that(ext, has_entry('Quantity', 10))
		assert_that(ext, has_entry('Coupon', "mycoupon"))
		assert_that(ext, is_not(has_key('PurchaseFee')))
		assert_that(ext, has_entry('PurchasePrice', 100))
		assert_that(ext, has_entry('NonDiscountedPrice', 105))
