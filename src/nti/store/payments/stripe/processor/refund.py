#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Stripe refund functionalilty.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import time
import functools
from datetime import date

import zope.intid
from zope import component
from zope.event import notify

from pyramid.threadlocal import get_current_request

from nti.dataserver import interfaces as nti_interfaces

from nti.store import NTIStoreException
from nti.store import get_possible_site_names
from nti.store import interfaces as store_interfaces

from nti.externalization import integer_strings

from .. import interfaces as stripe_interfaces

from .base import BaseProcessor

class RefundProcessor(BaseProcessor):

	def refund_purchase(self, trx_id, amount=None, refund_application_fee=None,
						api_key=None, request=None):
		"""
		Refunds to a purchase attempt
		"""
		request = request or get_current_request()
		site_names = get_possible_site_names(request, include_default=True)

		# prepare transaction runner
		transactionRunner = \
				component.getUtility(nti_interfaces.IDataserverTransactionRunner)
		transactionRunner = functools.partial(transactionRunner, site_names=site_names)

		if amount is not None and amount <= 0:
			raise NTIStoreException('Invalid refund amount')

		uid = integer_strings.from_external_string(trx_id)
		zope_iids = component.getUtility(zope.intid.IIntIds)
		purchase = zope_iids.queryObject(uid)
		if not purchase or not store_interfaces.IPurchaseAttempt.providedBy(purchase):
			raise NTIStoreException('Purchase attempt %s could not be found', trx_id)
		
		if not purchase.has_succeeded():
			raise NTIStoreException('Purchase attempt %s status is not completed',
									trx_id)
		elif purchase.is_refunded():
			logger.warn('Purchase attempt %s has already been refunded', trx_id)
			return False

		purchase_id = purchase.id
		api_key = api_key or self.get_api_key(purchase)
		if api_key is None:
			logger.error('Could not get a valid provider for purchase %r', purchase_id)
			return False

		pricing = purchase.Pricing
		if amount is not None and amount > pricing.TotalPurchasePrice:
			logger.warn('Refund amount is greater than the charge amount. Adjusting')
			amount = pricing.TotalPurchasePrice
			
		application_fee = pricing.TotalPurchaseFee
		if refund_application_fee is None:
			if application_fee:
				refund_application_fee = True
			else:
				refund_application_fee = False

		charge = None
		sp = stripe_interfaces.IStripePurchaseAttempt(purchase)
		if sp.ChargeID:
			charge = self.get_stripe_charge(sp.ChargeID, api_key=api_key)
		else:
			start_time = time.mktime(date.fromtimestamp(purchase.StartTime).timetuple())
			charges = self.get_charges(purchase_id=purchase_id, start_time=start_time,
									   api_key=api_key)
			if charges:
				charge = charges[0]  # get first
				# re-register for future use
				notify(stripe_interfaces.RegisterStripeCharge(purchase, charge.id))
			
		if charge:
			cents_amount = int(amount * 100.0) if amount is not None else None
			def do_refund():
				logger.debug('Refunding %s...', trx_id)
				local_purchase = zope_iids.queryObject(uid)
				if not charge.refunded:
					charge.refund(amount=cents_amount,
								  refund_application_fee=refund_application_fee)
				else:
					logger.warn('Stripe charge already refunded')
				notify(store_interfaces.PurchaseAttemptRefunded(local_purchase))
			transactionRunner(do_refund)

		else:
			raise NTIStoreException('Stripe purchase was found')

		return charge
