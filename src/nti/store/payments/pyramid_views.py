# -*- coding: utf-8 -*-
"""
Payment pyramid views.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from .stripe import pyramid_views as stripe_pyramid

def is_valid_amount(amount):
	try:
		amount = float(amount)
		return amount > 0
	except:
		return False

def is_valid_pve_int(value):
	try:
		value = float(value)
		return value > 0
	except:
		return False

# alias

StripePaymentView = stripe_pyramid.StripePaymentView
GetStripeConnectKeyView = stripe_pyramid.GetStripeConnectKeyView
ValidateStripeCouponView = stripe_pyramid.ValidateStripeCouponView
