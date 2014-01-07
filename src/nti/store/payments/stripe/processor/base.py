#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Stripe base processor functionalilty.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from nti.store import purchase_attempt

from .. import stripe_io
from .. import interfaces as stripe_interfaces

class BaseProcessor(stripe_io.StripeIO):

	name = 'stripe'

	def get_api_key(self, purchase):
		providers = purchase_attempt.get_providers(purchase)
		provider = providers[0] if providers else u''  # pick first provider
		stripe_key = component.queryUtility(stripe_interfaces.IStripeConnectKey,
											provider)
		return stripe_key.PrivateKey if stripe_key else None

	def get_charges(self, purchase_id=None, username=None, customer=None,
                    start_time=None, end_time=None, api_key=None):
		result = []
		for c in self.get_stripe_charges(start_time=start_time, end_time=end_time,
										 api_key=api_key):
			desc = c.description
			if  (purchase_id and purchase_id in desc) or \
				(username and username in desc) or \
				(customer and customer in desc):
				result.append(c)
		return result

	def create_card_token(self, customer_id=None, number=None, exp_month=None,
                          exp_year=None, cvc=None, api_key=None, **kwargs):
		token = self.create_stripe_token(customer_id, number, exp_month, exp_year,
                                         cvc, api_key, **kwargs)
		return token.id

