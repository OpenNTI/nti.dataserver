# -*- coding: utf-8 -*-
"""
Stripe payment module

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import interface
from zope.schema.fieldproperty import FieldPropertyStoredThroughField as FP

from ...purchase_error import PurchaseError
from . import interfaces as stripe_interfaces
from ...priced_purchasable import PricedPurchasable

@interface.implementer(stripe_interfaces.IStripeException)
class StripeException(Exception):
    pass

@interface.implementer(stripe_interfaces.IStripePurchaseError)
class StripePurchaseError(PurchaseError):
    HttpStatus = FP(stripe_interfaces.IStripePurchaseError['HttpStatus'])
    Param = FP(stripe_interfaces.IStripePurchaseError['Param'])

@interface.implementer(stripe_interfaces.IStripePricedPurchasable)
class StripePricedPurchasable(PricedPurchasable):

    Coupon = FP(stripe_interfaces.IStripePricedPurchasable['Coupon'])

    @classmethod
    def copy(cls, priced):
        result = StripePricedPurchasable(NTIID=priced.NTIID, PurchaseFee=priced.PurchaseFee,
                                         PurchasePrice=priced.PurchasePrice,
                                         NonDiscountedPrice=priced.NonDiscountedPrice)
        result.Coupon = getattr(priced, 'Coupon', None)
        return result
