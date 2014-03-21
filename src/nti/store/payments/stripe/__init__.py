#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Stripe payment module

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope.schema.fieldproperty import FieldPropertyStoredThroughField as FP

from ...purchase_error import PurchaseError
from . import interfaces as stripe_interfaces

# make sure str and unicode are interfaced marked
from dolmen.builtins import IString, IUnicode

@interface.implementer(stripe_interfaces.IStripeException)
class StripeException(Exception):
	pass

class InvalidStripeCoupon(StripeException):
	pass

class NoSuchStripeCoupon(StripeException):
	pass

@interface.implementer(stripe_interfaces.IStripePurchaseError)
class StripePurchaseError(PurchaseError):
	HttpStatus = FP(stripe_interfaces.IStripePurchaseError['HttpStatus'])
	Param = FP(stripe_interfaces.IStripePurchaseError['Param'])
