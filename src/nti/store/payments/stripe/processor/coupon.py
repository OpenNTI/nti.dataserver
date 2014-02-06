#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Stripe purchase coupon functionality.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six
import time

from nti.store.payments import _BasePaymentProcessor
from nti.store.payments.stripe import InvalidStripeCoupon
from nti.store.payments.stripe.processor.base import BaseProcessor

class CouponProcessor(_BasePaymentProcessor, BaseProcessor):

    def get_coupon(self, coupon, api_key=None):
        result = self.get_stripe_coupon(coupon, api_key=api_key) \
                 if isinstance(coupon, six.string_types) else coupon
        return result

    def validate_coupon(self, coupon, api_key=None):
        coupon = self.get_stripe_coupon(coupon, api_key=api_key) \
                 if isinstance(coupon, six.string_types) else coupon
        result = (coupon is not None)
        if result:
            if coupon.duration == u'repeating':
                result = \
                    (coupon.duration_in_months is None or coupon.duration_in_months > 0) and \
                    (coupon.max_redemptions is None or coupon.max_redemptions > 0) and \
                    (coupon.redeem_by is None or time.time() <= coupon.redeem_by)
            elif coupon.duration == u'once':
                result = coupon.redeem_by is None or time.time() <= coupon.redeem_by
        return result

    def get_and_validate_coupon(self, coupon=None, api_key=None):
        coupon = self.get_coupon(coupon, api_key=api_key) if coupon else None
        if coupon is not None and not self.validate_coupon(coupon, api_key=api_key):
            raise InvalidStripeCoupon()
        return coupon

    def apply_coupon(self, amount, coupon, api_key=None):
        coupon = self.get_stripe_coupon(coupon, api_key=api_key) \
                 if isinstance(coupon, six.string_types) else coupon
        if coupon:
            if coupon.percent_off is not None:
                pcnt = coupon.percent_off / 100.0 \
                       if coupon.percent_off > 1 else coupon.percent_off
                amount = amount * (1 - pcnt)
            elif coupon.amount_off is not None:
                amount_off = coupon.amount_off / 100.0
                amount -= amount_off
        return float(max(0, amount))
