# -*- coding: utf-8 -*-
"""
Stripe utilities.

$Id: stripe_processor.py 18438 2013-04-19 04:17:47Z carlos.sanchez $
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface

from . import StripeException
from . import StripePricedPurchasable
from . import interfaces as stripe_interfaces
from ... import interfaces as store_interfaces

class InvalidStripeCoupon(StripeException):
    pass

@interface.implementer(stripe_interfaces.IStripePurchasablePricer)
class StripePurchasablePricer(object):

    processor = "stripe"

    def price(self, purchasable, quantity=1, coupon=None):
        pricer = component.getUtility(store_interfaces.IPurchasablePricer)
        priced = StripePricedPurchasable.copy(pricer.price(purchasable, quantity))

        provider = priced.Provider or u''
        stripe_key = component.queryUtility(stripe_interfaces.IStripeConnectKey, provider)

        purchase_price = priced.PurchasePrice
        manager = component.getUtility(store_interfaces.IPaymentProcessor, name=self.processor)

        if coupon is not None and stripe_key:
            # stripe defines an 80 sec timeout for http requests
            # at this moment we are to wait for coupon validation
            s_coupon = manager.get_coupon(coupon, api_key=stripe_key.PrivateKey)
            if s_coupon is not None:
                validated_coupon = manager.validate_coupon(s_coupon, api_key=stripe_key.PrivateKey)
                if not validated_coupon:
                    raise InvalidStripeCoupon()
            priced.Coupon = s_coupon

            priced.NonDiscountedPrice = purchase_price
            purchase_price = manager.apply_coupon(purchase_price, coupon)
            priced.PurchasePrice = purchase_price

        return priced
