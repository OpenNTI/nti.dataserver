# -*- coding: utf-8 -*-
"""
Payment pyramid views.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from .stripe import pyramid_views as stripe_pyramid

# alias

StripePaymentView = stripe_pyramid.StripePaymentView
CreateStripeTokenView = stripe_pyramid.CreateStripeTokenView
GetStripeConnectKeyView = stripe_pyramid.GetStripeConnectKeyView
StripeRefundPaymentView = stripe_pyramid.StripeRefundPaymentView
GeneratePurchaseInvoiceWitStripe = stripe_pyramid.GeneratePurchaseInvoiceWitStripe
PricePurchasableWithStripeCouponView = stripe_pyramid.PricePurchasableWithStripeCouponView
