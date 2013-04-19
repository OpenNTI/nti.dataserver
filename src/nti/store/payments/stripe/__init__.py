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

@interface.implementer(stripe_interfaces.IStripePurchaseError)
class StripePurchaseError(PurchaseError):

    HttpStatus = FP(stripe_interfaces.IStripePurchaseError['HttpStatus'])
    Param = FP(stripe_interfaces.IStripePurchaseError['Param'])
