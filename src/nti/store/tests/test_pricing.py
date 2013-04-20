#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from zope import component

from .. import pricing
from .. import interfaces as store_interfaces

from . import ConfiguringTestBase

from hamcrest import (assert_that, has_length, is_not, none, is_)

class TestPurchasableStore(ConfiguringTestBase):

	def test_price(self):
		pricer = component.getUtility(store_interfaces.IPurchasablePricer)
		p = pricing.create_priceable(u"iid_0", 10)
		priced = pricer.price(p)
		assert_that(priced, is_not(none()))
		assert_that(priced.NTIID, is_(u'iid_0'))
		assert_that(priced.PurchaseFee, is_(200))
		assert_that(priced.PurchasePrice, is_(1000))
		assert_that(priced.Quantity, is_(10))

	def test_evaluate(self):
		pricer = component.getUtility(store_interfaces.IPurchasablePricer)
		p0 = pricing.create_priceable(u"iid_0", 5)
		p1 = pricing.create_priceable(u"iid_1", 7)
		result = pricer.evaluate((p0, p1))
		assert_that(result, is_not(none()))
		assert_that(result.PricedList, has_length(2))
		assert_that(result.TotalPurchaseFee, is_(100))
		assert_that(result.TotalPurchasePrice, is_(1340))
