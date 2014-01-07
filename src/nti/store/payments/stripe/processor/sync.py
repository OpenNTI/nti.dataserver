#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Stripe purchase functionalilty.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import time
from datetime import date

from zope.event import notify

from pyramid.threadlocal import get_current_request

from nti.dataserver.users import User

from nti.store import purchase_history
from nti.store import interfaces as store_interfaces

from .. import utils
from .. import interfaces as stripe_interfaces

from .base import BaseProcessor

class SyncProcessor(BaseProcessor):

	def sync_purchase(self, purchase_id, username, api_key=None):
		"""
		Attempts to synchronize a purchase attempt with the information collected in
		stripe.com and/or local db.
		"""
		user = User.get_user(username)
		purchase = purchase_history.get_purchase_attempt(purchase_id, username)
		if purchase is None:
			logger.error('Purchase %r for user %s could not be found in dB',
						  purchase_id, username)
			return None

		api_key = api_key or self.get_api_key(purchase)
		if api_key is None:
			logger.error('Could not get a valid provider for purchase %r', purchase_id)
			return None

		charge = None
		message = None
		do_synch = False
		sp = stripe_interfaces.IStripePurchaseAttempt(purchase)
		if sp.ChargeID:
			charge = self.get_stripe_charge(sp.ChargeID, api_key=api_key)
			if charge is None:
				# if the charge cannot be found it means there was a db error
				# or the charge has been deleted from stripe.
				message = "Charge %s cannot be found in Stripe" % sp.ChargeID
				logger.warn('Charge %s for purchase %r/%s could not be found in Stripe',
							sp.ChargeID, purchase_id, user)
		else:
			start_time = time.mktime(date.fromtimestamp(purchase.StartTime).timetuple())
			charges = self.get_charges(purchase_id=purchase_id, start_time=start_time,
									   api_key=api_key)
			if charges:
				charge = charges[0]
				notify(stripe_interfaces.RegisterStripeCharge(purchase, charge.id))
			elif sp.TokenID:
				token = self.get_stripe_token(sp.TokenID, api_key=api_key)
				if token is None:
					# if the token cannot be found it means there was a db error
					# or the token has been deleted from stripe.
					message = 'Token %s could not found in Stripe' % sp.TokenID
					logger.warn('Token %s for purchase %r/%s could not found in Stripe',
								sp.TokenID, purchase_id, username)
					if not purchase.has_completed():
						do_synch = True
						notify(store_interfaces.PurchaseAttemptFailed(
													purchase,
													utils.adapt_to_error(message)))
				elif token.used:
					tid = sp.TokenID
					message = "Token %s has been used and no charge was found" % tid
					logger.warn(message)
					if not purchase.has_completed():
						do_synch = True
						notify(store_interfaces.PurchaseAttemptFailed(
													purchase,
													utils.adapt_to_error(message)))
				elif not purchase.is_pending():  # no charge and unused token
					logger.warn('No charge and unused token. Incorrect status for ' +
								'purchase %r/%s', purchase_id, username)

		if charge:
			do_synch = True
			if charge.paid and not purchase.has_succeeded():
				pc = utils.create_payment_charge(charge)
				request = get_current_request()
				notify(store_interfaces.PurchaseAttemptSuccessful(purchase, pc, request))
			elif charge.failure_message and not purchase.has_failed():
				notify(store_interfaces.PurchaseAttemptFailed(
										purchase,
										utils.adapt_to_error(charge.failure_message)))
			elif charge.refunded and not purchase.is_refunded():
				notify(store_interfaces.PurchaseAttemptRefunded(purchase))

		elif time.time() - purchase.StartTime >= 180 and not purchase.has_completed():
			do_synch = True
			message = message or "Failed purchase after expiration time"
			notify(store_interfaces.PurchaseAttemptFailed(
										purchase,
										utils.adapt_to_error(message)))

		if do_synch:
			notify(store_interfaces.PurchaseAttemptSynced(purchase))
		return charge
