#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Stripe purchase functionalilty.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import sys
import math
import functools

from zope import component
from zope.event import notify

from pyramid.threadlocal import get_current_request

from nti.dataserver import interfaces as nti_interfaces

from nti.store import purchase_history
from nti.store import NTIStoreException
from nti.store import get_possible_site_names
from nti.store import interfaces as store_interfaces

from .coupon import CouponProcessor
from .pricing import PricingProcessor

from .. import utils
from .. import stripe_customer
from .. import interfaces as stripe_interfaces

class PurchaseProcessor(stripe_customer.StripeCustomer,
						CouponProcessor,
						PricingProcessor):

	def process_purchase(self, purchase_id, username, token, expected_amount=None,
						 api_key=None, request=None):
		"""
		Executes the process purchase.
		This function may be called in a greenlet
		(which cannot be run within a transaction runner);
		the request should be established when it is called.
		"""
		request = request or get_current_request()
		site_names = get_possible_site_names(request, include_default=True)

		# prepare transaction runner
		transactionRunner = \
				component.getUtility(nti_interfaces.IDataserverTransactionRunner)
		transactionRunner = functools.partial(transactionRunner, site_names=site_names)

		def start_purchase():
			purchase = purchase_history.get_purchase_attempt(purchase_id, username)
			if purchase is None:
				raise NTIStoreException(
							"Could not find purchase attempt with id %s" % purchase_id)

			if not purchase.is_pending():
				notify(store_interfaces.PurchaseAttemptStarted(purchase))

			# price purchase
			pricing = self.do_pricing(purchase)
			return pricing

		def register_stripe_user():
			purchase = purchase_history.get_purchase_attempt(purchase_id, username)
			if not purchase.has_completed():
				logger.info('Getting/Creating Stripe Customer for %s', username)
				customer_id = self.get_or_create_customer(username, api_key=api_key)
				notify(stripe_interfaces.RegisterStripeToken(purchase, token))
				return customer_id
			return None

		try:
			# start the purchase and price trx
			pricing = transactionRunner(start_purchase)
			currency = pricing.Currency
			amount = pricing.TotalPurchasePrice
			application_fee = pricing.TotalPurchaseFee \
							  if pricing.TotalPurchaseFee else None
			if 	expected_amount is not None and \
				not math.fabs(expected_amount - amount) <= 0.05:
				logger.error("Purchase order amount %.2f did not match the " +
							 "expected amount %.2f", amount, expected_amount)
				raise NTIStoreException(
							"Purchase order amount did not match the expected amount")

			# create a stripe customer
			customer_id = transactionRunner(register_stripe_user)

			# get price amount in cents
			cents_amount = int(amount * 100.0)
			application_fee = int(application_fee * 100.0) if application_fee else None

			# contact stripe
			def do_stripe_purchase():
				charge = None
				purchase = purchase_history.get_purchase_attempt(purchase_id, username)
				if purchase.is_pending() and customer_id is not None:
					# charge card, user description for tracking purposes
					descid = utils.encode_charge_description(purchase_id,
															 username,
															 customer_id)
					logger.info('Creating stripe charge for %s', purchase_id)
					charge = self.create_charge(cents_amount, currency=currency,
												card=token, description=descid,
												application_fee=application_fee,
												api_key=api_key)
				return charge

			charge = transactionRunner(do_stripe_purchase)

			if charge is not None:
				# register charge
				def register_charge_notify():
					purchase = purchase_history.get_purchase_attempt(purchase_id,
																	 username)
					if not purchase.is_pending():
						return

					notify(stripe_interfaces.RegisterStripeCharge(purchase, charge.id))
					if charge.paid:
						# notify success
						purchase.Pricing = pricing
						payment_charge = utils.create_payment_charge(charge)
						notify(store_interfaces.PurchaseAttemptSuccessful(purchase,
																		  payment_charge,
																		  request))

						# update coupon. In case there is an error updating the coupon
						# (e.g. max redemptions reached) the we will still the transaction go.
						# Log error and this must be check manually
						coupon = purchase.Order.Coupon
						if coupon is not None:
							try:
								self.update_customer(username, coupon=coupon,
													 api_key=api_key)
							except Exception:
								logger.exception("Exception while updating the user " +
												 "coupon. The charge is still valid")

				transactionRunner(register_charge_notify)

			# return charge id
			return charge.id if charge is not None else None
		except Exception as e:
			logger.exception("Cannot complete process purchase for '%s'", purchase_id)
			t, v, tb = sys.exc_info()
			error = utils.adapt_to_error(e)
			# fail purchase in a trx
			def fail_purchase():
				purchase = purchase_history.get_purchase_attempt(purchase_id, username)
				if purchase is not None:
					notify(store_interfaces.PurchaseAttemptFailed(purchase, error))
			transactionRunner(fail_purchase)
			# report exception
			raise t, v, tb

