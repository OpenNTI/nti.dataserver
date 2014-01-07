#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Stripe purchase pricing functionalilty.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from nti.store import purchase_history
from nti.store import interfaces as store_interfaces

from .base import BaseProcessor

class PricingProcessor(BaseProcessor):

	def do_pricing(self, purchase_attempt):
		pricer = component.getUtility(store_interfaces.IPurchasablePricer,
									  name=self.name)
		result = pricer.evaluate(purchase_attempt.Order)
		return result
	_do_pricing = do_pricing  # BWC

	def price_purchase(self, purchase_id, username):
		purchase = purchase_history.get_purchase_attempt(purchase_id, username)
		result = self.do_pricing(purchase)
		return result
