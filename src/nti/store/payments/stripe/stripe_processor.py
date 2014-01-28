#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Stripe processor functionalilty.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from . import interfaces as stripe_interfaces

from .processor import SyncProcessor
from .processor import EventProcessor
from .processor import RefundProcessor
from .processor import PurchaseProcessor

@interface.implementer(stripe_interfaces.IStripePaymentProcessor)
class StripePaymentProcessor(PurchaseProcessor, SyncProcessor, EventProcessor,
							 RefundProcessor):
	pass
