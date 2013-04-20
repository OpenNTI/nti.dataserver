# -*- coding: utf-8 -*-
"""
Stripe utilities.

$Id: stripe_processor.py 18438 2013-04-19 04:17:47Z carlos.sanchez $
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import six

from zope import component

from . import InvalidStripeCoupon
from ...utils import to_collection
from . import StripePricedPurchasable
from . import interfaces as stripe_interfaces
from ... import interfaces as store_interfaces
from ...pricing import create_pricing_results, DefaultPurchasablePricer

def makenone(s, default=None):
    if isinstance(s, six.string_types):
        s = default if s == 'None' else unicode(s)
    return s

class StripePurchasablePricer(DefaultPurchasablePricer):

    processor = "stripe"

    def get_coupon(self, coupon=None, api_key=None):
        manager = component.getUtility(store_interfaces.IPaymentProcessor, name=self.processor)
        if coupon is not None and api_key:
            # stripe defines an 80 sec timeout for http requests
            # at this moment we are to wait for coupon validation
            if isinstance(coupon, six.string_types):
                coupon = manager.get_coupon(coupon, api_key=api_key)
            if coupon is not None:
                validated_coupon = manager.validate_coupon(coupon, api_key=api_key)
                if not validated_coupon:
                    raise InvalidStripeCoupon()
        return coupon

    def price(self, priceable):
        priced = super(StripePurchasablePricer, self).price(priceable)
        priced = StripePricedPurchasable.copy(priced)
        coupon = getattr(priceable, 'Coupon', None)

        manager = component.getUtility(store_interfaces.IPaymentProcessor, name=self.processor)
        stripe_key = component.queryUtility(stripe_interfaces.IStripeConnectKey, priced.Provider)

        purchase_price = priced.PurchasePrice

        if coupon is not None and stripe_key:
            priced.Coupon = self.get_coupon(coupon, stripe_key.PrivateKey)
            if priced.Coupon is not None:
                priced.NonDiscountedPrice = purchase_price
                purchase_price = manager.apply_coupon(purchase_price, priced.Coupon)
                priced.PurchasePrice = purchase_price
                priced.PurchaseFee = self.calc_fee(purchase_price, priceable.Fee)
        return priced

    def evaluate(self, priceables):
        priceables = to_collection(priceables)

        total_fee = 0
        total_amount = 0
        total_non_discount = 0
        result = create_pricing_results(non_discounted_price=0.0)
        for priceable in priceables:
            priced = self.price(priceable)
            result.PricedList.append(priced)
            total_fee += priced.PurchaseFee
            total_amount += priced.PurchasePrice
            total_non_discount += priced.NonDiscountedPrice or priced.PurchasePrice

        # set totals
        result.TotalPurchaseFee = total_fee
        result.TotalPurchasePrice = total_amount
        result.TotalNonDiscountedPrice = total_non_discount
        return result

