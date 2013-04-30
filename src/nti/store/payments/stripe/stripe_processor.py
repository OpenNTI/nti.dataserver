# -*- coding: utf-8 -*-
"""
Stripe purchase functionalilty.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import sys
import six
import math
import time
import functools
import simplejson as json
from datetime import date

from zope import component
from zope import interface
from zope.event import notify

from pyramid.threadlocal import get_current_request

from nti.dataserver.users import User
from nti.dataserver import interfaces as nti_interfaces

from . import utils
from . import stripe_io
from . import stripe_customer
from . import StripeException
from nti.store import purchase_history
from nti.store import purchase_attempt
from . import interfaces as stripe_interfaces
from nti.store.payments import _BasePaymentProcessor
from nti.store import interfaces as store_interfaces


@interface.implementer(stripe_interfaces.IStripePaymentProcessor)
class StripePaymentProcessor(_BasePaymentProcessor, stripe_customer._StripeCustomer, stripe_io.StripeIO):

	name = 'stripe'
	events = ("charge.succeeded", "charge.refunded", "charge.failed", "charge.dispute.created", "charge.dispute.updated")

	def create_card_token(self, customer_id=None, number=None, exp_month=None, exp_year=None, cvc=None, api_key=None, **kwargs):
		token = self.create_stripe_token(customer_id, number, exp_month, exp_year, cvc, api_key, **kwargs)
		return token.id

	def create_charge(self, amount, currency='USD', customer_id=None, card=None, description=None,
					  application_fee=None, api_key=None):
		charge = self.create_stripe_charge(amount=amount, currency=currency, customer_id=customer_id,
										   card=card, description=description, application_fee=application_fee,
										   api_key=api_key)
		if charge.failure_message:
			raise stripe_io.StripeException(charge.failure_message)
		return charge

	# ---------------------------

	def get_coupon(self, coupon, api_key=None):
		result = self.get_stripe_coupon(coupon, api_key=api_key) if isinstance(coupon, six.string_types) else coupon
		return result

	def validate_coupon(self, coupon, api_key=None):
		coupon = self.get_stripe_coupon(coupon, api_key=api_key) if isinstance(coupon, six.string_types) else coupon
		result = (coupon is not None)
		if result:
			if coupon.duration == u'repeating':
				result = (coupon.duration_in_months is None or coupon.duration_in_months > 0) and \
						 (coupon.max_redemptions is None or coupon.max_redemptions > 0) and \
						 (coupon.redeem_by is None or time.time() <= coupon.redeem_by)
			elif coupon.duration == u'once':
				result = coupon.redeem_by is None or time.time() <= coupon.redeem_by
		return result

	def get_and_validate_coupon(self, coupon=None, api_key=None):
		coupon = self.get_coupon(coupon, api_key=api_key) if coupon else None
		if coupon is not None and not self.validate_coupon(coupon, api_key=api_key):
			raise ValueError("Invalid coupon")
		return coupon

	def apply_coupon(self, amount, coupon, api_key=None):
		coupon = self.get_stripe_coupon(coupon, api_key=api_key) if isinstance(coupon, six.string_types) else coupon
		if coupon:
			if coupon.percent_off is not None:
				pcnt = coupon.percent_off / 100.0 if coupon.percent_off > 1 else coupon.percent_off
				amount = amount * (1 - pcnt)
			elif coupon.amount_off is not None:
				amount_off = coupon.amount_off / 100.0
				amount -= amount_off
		return float(max(0, amount))

	def _do_pricing(self, purchase_attempt):
		pricer = component.getUtility(store_interfaces.IPurchasablePricer, name="stripe")
		result = pricer.evaluate(purchase_attempt.Order)
		return result

	def price_purchase(self, purchase_id, username):
		purchase = purchase_history.get_purchase_attempt(purchase_id, username)
		result = self._do_pricing(purchase)
		return result

	def process_purchase(self, purchase_id, username, token, expected_amount=None, api_key=None, request=None):
		"""
		Executes the process purchase.
		This function may be called in a greenlet (which cannot be run within a transaction runner)
		"""
		#### from IPython.core.debugger import Tracer; Tracer()() ####

		# capture the site names so the purchasables
		# can be read by sub-transactions
		from nti.appserver import site_policies
		request = request or get_current_request()
		site_names = site_policies.get_possible_site_names(request, include_default=True)

		# prepare transaction runner
		transactionRunner = component.getUtility(nti_interfaces.IDataserverTransactionRunner)
		transactionRunner = functools.partial(transactionRunner, site_names=site_names)

		def start_purchase():
			purchase = purchase_history.get_purchase_attempt(purchase_id, username)
			if purchase is None:
				raise StripeException("Could not find purchase attempt with id %s" % purchase_id)

			if not purchase.is_pending():
				notify(store_interfaces.PurchaseAttemptStarted(purchase))

			# price purchase
			pricing = self._do_pricing(purchase)
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
			application_fee = pricing.TotalPurchaseFee if pricing.TotalPurchaseFee else None
			if expected_amount is not None and not math.fabs(expected_amount - amount) <= 0.05:
				logger.error("Purchase order amount %.2f did not match the expected amount %.2f", amount, expected_amount)
				raise StripeException("Purchase order amount did not match the expected amount")

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
					descid = utils.encode_charge_description(purchase_id, username, customer_id)
					logger.info('Creating stripe charge for %s', purchase_id)
					charge = self.create_charge(cents_amount, currency=currency, card=token, description=descid,
												application_fee=application_fee, api_key=api_key)
				return charge

			charge = transactionRunner(do_stripe_purchase)

			if charge is not None:
				# register charge
				def register_charge_notify():
					purchase = purchase_history.get_purchase_attempt(purchase_id, username)
					if not purchase.is_pending():
						return

					notify(stripe_interfaces.RegisterStripeCharge(purchase, charge.id))
					if charge.paid:
						# notify success
						purchase.Pricing = pricing
						pc = utils.create_payment_charge(charge)
						notify(store_interfaces.PurchaseAttemptSuccessful(purchase, pc, request))

						# update coupon. In case there is an error updating the coupon (e.g. max redemptions reached)
						# the we will still the transaction go. Log error and this must be check manually
						coupon = purchase.Order.Coupon
						if coupon is not None:
							try:
								self.update_customer(username, coupon=coupon, api_key=api_key)
							except Exception:
								logger.exception("Exception while updating the user coupon. The charge is still valid")

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

	def get_charges(self, purchase_id=None, username=None, customer=None, start_time=None, end_time=None, api_key=None):
		result = []
		for c in self.get_stripe_charges(start_time=start_time, end_time=end_time, api_key=api_key):
			desc = c.description
			if (purchase_id and purchase_id in desc) or (username and username in desc) or (customer and customer in desc):
				result.append(c)
		return result

	def get_api_key(self, purchase):
		providers = purchase_attempt.get_providers(purchase)
		provider = providers[0] if providers else u''  # pick first provider
		stripe_key = component.queryUtility(stripe_interfaces.IStripeConnectKey, provider)
		return stripe_key.PrivateKey if stripe_key else None

	def sync_purchase(self, purchase_id, username, api_key=None):
		"""
		Attempts to synchronize a purchase attempt with the information collected in
		stripe.com and/or local db.
		"""
		user = User.get_user(username)
		purchase = purchase_history.get_purchase_attempt(purchase_id, username)
		if purchase is None:
			logger.error('Purchase %r for user %s could not be found in dB', purchase_id, username)
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
				logger.warn('Charge %s for purchase %r/%s could not be found in Stripe', sp.ChargeID, purchase_id, user)
		else:
			start_time = time.mktime(date.fromtimestamp(purchase.StartTime).timetuple())
			charges = self.get_charges(purchase_id=purchase_id, start_time=start_time, api_key=api_key)
			if charges:
				charge = charges[0]
				notify(stripe_interfaces.RegisterStripeCharge(purchase, charge.id))
			elif sp.TokenID:
				token = self.get_stripe_token(sp.TokenID, api_key=api_key)
				if token is None:
					# if the token cannot be found it means there was a db error
					# or the token has been deleted from stripe.
					message = 'Token %s could not found in Stripe' % sp.TokenID
					logger.warn('Token %s for purchase %r/%s could not found in Stripe', sp.TokenID, purchase_id, username)
					if not purchase.has_completed():
						do_synch = True
						notify(store_interfaces.PurchaseAttemptFailed(purchase, utils.adapt_to_error(message)))
				elif token.used:
					message = "Token %s has been used and no charge was found" % sp.TokenID
					logger.warn(message)
					if not purchase.has_completed():
						do_synch = True
						notify(store_interfaces.PurchaseAttemptFailed(purchase, utils.adapt_to_error(message)))
				elif not purchase.is_pending():  # no charge and unused token
					logger.warn('No charge and unused token. Incorrect status for purchase %r/%s', purchase_id, username)

		if charge:
			do_synch = True
			if charge.paid and not purchase.has_succeeded():
				pc = utils.create_payment_charge(charge)
				request = get_current_request()
				notify(store_interfaces.PurchaseAttemptSuccessful(purchase, pc, request))
			elif charge.failure_message and not purchase.has_failed():
				notify(store_interfaces.PurchaseAttemptFailed(purchase, utils.adapt_to_error(charge.failure_message)))
			elif charge.refunded and not purchase.is_refunded():
				notify(store_interfaces.PurchaseAttemptRefunded(purchase))

		elif time.time() - purchase.StartTime >= 180 and not purchase.has_completed():
			do_synch = True
			message = message or "Failed purchase after expiration time"
			notify(store_interfaces.PurchaseAttemptFailed(purchase, utils.adapt_to_error(message)))

		if do_synch:
			notify(store_interfaces.PurchaseAttemptSynced(purchase))
		return charge

	def process_event(self, body):
		request = get_current_request()
		try:
			event = json.loads(body) if isinstance(body, six.string_types) else body
			etype = event.get('type', None)
			data = event.get('data', {})
			if etype in self.events:
				data = utils.decode_charge_description(data.get('description', u''))
				purchase_id = data.get('PurchaseID', u'')
				username = data.get('Username', u'')
				purchase = purchase_history.get_purchase_attempt(purchase_id, username)
				if purchase:
					if etype in ("charge.succeeded") and not purchase.has_succeeded():
						pc = None
						api_key = self.get_api_key(purchase)
						if api_key:
							charges = self.get_charges(purchase_id=purchase_id, start_time=purchase.StartTime, api_key=api_key)
							pc = utils.create_payment_charge(charges[0]) if charges else None
						notify(store_interfaces.PurchaseAttemptSuccessful(purchase, pc, request))
					elif etype in ("charge.refunded") and not purchase.is_refunded():
						notify(store_interfaces.PurchaseAttemptRefunded(purchase))
					elif etype in ("charge.failed") and not purchase.has_failed():
						notify(store_interfaces.PurchaseAttemptFailed(purchase))
					elif etype in ("charge.dispute.created", "charge.dispute.updated") and not purchase.is_disputed():
						notify(store_interfaces.PurchaseAttemptDisputed(purchase))
			else:
				logger.debug('Unhandled event type (%s)' % etype)
			return True
		except Exception:
			logger.exception('Error processing stripe event (webhook)')
			return False
