# -*- coding: utf-8 -*-
"""
Stripe purchase functionalilty.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six
import math
import time
import functools
import simplejson as json
from datetime import date

from zope import component
from zope import interface
from zope.event import notify

from nti.dataserver.users import User
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.users import interfaces as user_interfaces

from . import stripe_io
from .utils import makenone
from . import StripeException
from .. import _BasePaymentProcessor
from nti.store import payment_charge
from nti.store import purchase_history
from nti.store import purchase_attempt
from . import interfaces as stripe_interfaces
from nti.store import interfaces as store_interfaces

def _create_user_address(charge):
	card = getattr(charge, 'card', None)
	if card is not None:
		address = payment_charge.UserAddress.create(makenone(card.address_line1),
 													makenone(card.address_line2),
 													makenone(card.address_city),
 													makenone(card.address_state),
 													makenone(card.address_zip),
 													makenone(card.address_country))
		return address
	else:
		return None

def _get_card_info(charge):
	card = getattr(charge, 'card', None)
	name = getattr(card, 'name', None)
	last4 = getattr(card, 'last4', None)
	last4 = int(last4) if last4 is not None else None
	return (last4, name)

def _create_payment_charge(charge):
	amount = charge.amount / 100.0
	currency = charge.currency.upper()
	last4, name = _get_card_info(charge)
	address = _create_user_address(charge)
	created = float(charge.created or time.time())
	result = payment_charge.PaymentCharge(Amount=amount, Currency=currency, Created=created,
										  CardLast4=last4, Address=address, Name=name)
	return result

def _adapt_to_error(e):
	result = stripe_interfaces.IStripePurchaseError(e, None)
	if result is None and isinstance(e, Exception):
		result = stripe_interfaces.IStripePurchaseError(StripeException(e.args), None)
	return result

def _encode_description(purchase_id, username, customer_id):
	data = {'PurchaseID': purchase_id, 'Username':username, 'CustomerID': customer_id}
	result = json.dumps(data)
	return result

def _decode_description(s):
	try:
		result = json.loads(s)
	except (TypeError, ValueError):
		result = {}
	return result

@interface.implementer(stripe_interfaces.IStripePaymentProcessor)
class _StripePaymentProcessor(_BasePaymentProcessor, stripe_io.StripeIO):

	name = 'stripe'
	events = ("charge.succeeded", "charge.refunded", "charge.failed", "charge.dispute.created", "charge.dispute.updated")

	def create_customer(self, user, api_key=None):
		user = User.get_user(str(user)) if not nti_interfaces.IUser.providedBy(user) else user

		profile = user_interfaces.IUserProfile(user)
		email = getattr(profile, 'email', None)
		description = getattr(profile, 'description', None)

		customer = self.create_stripe_customer(email, description, api_key)
		notify(stripe_interfaces.StripeCustomerCreated(user, customer.id))

		return customer

	def get_or_create_customer(self, user, api_key=None):
		user = User.get_user(str(user)) if not nti_interfaces.IUser.providedBy(user) else user
		adapted = stripe_interfaces.IStripeCustomer(user)
		if adapted.customer_id is None:
			customer = self.create_customer(user, api_key)
			result = customer.id
		else:
			result = adapted.customer_id
		return result

	def delete_customer(self, user, api_key=None):
		result = False
		user = User.get_user(str(user)) if not nti_interfaces.IUser.providedBy(user) else user
		adapted = stripe_interfaces.IStripeCustomer(user)
		if adapted.customer_id:
			result = self.delete_stripe_customer(customer_id=adapted.customer_id, api_key=api_key)
			notify(stripe_interfaces.StripeCustomerDeleted(user, adapted.customer_id))
		return result

	def update_customer(self, user, customer=None, api_key=None):
		user = User.get_user(str(user)) if not nti_interfaces.IUser.providedBy(user) else user
		profile = user_interfaces.IUserProfile(user)
		email = getattr(profile, 'email', None)
		description = getattr(profile, 'description', None)
		adapted = stripe_interfaces.IStripeCustomer(user)
		if adapted.customer_id:
			result = self.update_stripe_customer(customer=customer or adapted.customer_id,
												 email=email,
												 description=description,
												 api_key=api_key)
			return result

		return False

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
		return max(0, amount)

	def _do_pricing(self, purchase_attempt):
		pricer = component.getUtility(store_interfaces.IPurchasablePricer, name="stripe")
		result = pricer.evaluate(purchase_attempt.Order)
		return result

	def price_purchase(self, purchase_id, username):
		purchase = purchase_history.get_purchase_attempt(purchase_id, username)
		result = self._do_pricing(purchase)
		return result

	def process_purchase(self, purchase_id, username, token, expected_amount=None, api_key=None, site_names=()):
		"""
		Executes the process purchase.
		This function may be called in a greenlet (which cannot be run within a transaction runner)
		"""
		#### from IPython.core.debugger import Tracer; Tracer()() ####

		transactionRunner = component.getUtility(nti_interfaces.IDataserverTransactionRunner)
		transactionRunner = functools.partial(transactionRunner, site_names=site_names)

		def start_purchase():
			purchase = purchase_history.get_purchase_attempt(purchase_id, username)
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
			# start the purchase
			pricing = transactionRunner(start_purchase)
			currency = pricing.Currency
			amount = pricing.TotalPurchasePrice
			application_fee = pricing.TotalPurchaseFee if pricing.TotalPurchaseFee else None
			if expected_amount is not None and not math.fabs(expected_amount - amount) <= 0.05:
				logger.error("Purchase order amount %.2f did not match the expected amount %.2f", amount, expected_amount)
				raise Exception("Purchase order amount did not match the expected amount")

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
					descid = _encode_description(purchase_id, username, customer_id)
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
						purchase.Pricing = pricing
						pc = _create_payment_charge(charge)
						notify(store_interfaces.PurchaseAttemptSuccessful(purchase, pc))
				transactionRunner(register_charge_notify)

			# return charge id
			return charge.id if charge is not None else None
		except Exception as e:
			logger.exception("Cannot complete process purchase for '%s'" % purchase_id)
			error = _adapt_to_error(e)
			# fail purchase in a trx
			def fail_purchase():
				purchase = purchase_history.get_purchase_attempt(purchase_id, username)
				if purchase is not None:
					notify(store_interfaces.PurchaseAttemptFailed(purchase, error))
			transactionRunner(fail_purchase)

	# ---------------------------

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
						notify(store_interfaces.PurchaseAttemptFailed(purchase, _adapt_to_error(message)))
				elif token.used:
					message = "Token %s has been used and no charge was found" % sp.TokenID
					logger.warn(message)
					if not purchase.has_completed():
						do_synch = True
						notify(store_interfaces.PurchaseAttemptFailed(purchase, _adapt_to_error(message)))
				elif not purchase.is_pending():  # no charge and unused token
					logger.warn('No charge and unused token. Incorrect status for purchase %r/%s', purchase_id, username)

		if charge:
			do_synch = True
			if charge.paid and not purchase.has_succeeded():
				pc = _create_payment_charge(charge)
				notify(store_interfaces.PurchaseAttemptSuccessful(purchase, pc))
			elif charge.failure_message and not purchase.has_failed():
				notify(store_interfaces.PurchaseAttemptFailed(purchase, _adapt_to_error(charge.failure_message)))
			elif charge.refunded and not purchase.is_refunded():
				notify(store_interfaces.PurchaseAttemptRefunded(purchase))

		elif time.time() - purchase.StartTime >= 180 and not purchase.has_completed():
			do_synch = True
			message = message or "Failed purchase after expiration time"
			notify(store_interfaces.PurchaseAttemptFailed(purchase, _adapt_to_error(message)))

		if do_synch:
			notify(store_interfaces.PurchaseAttemptSynced(purchase))
		return charge

	def process_event(self, body):
		try:
			event = json.loads(body) if isinstance(body, six.string_types) else body
			etype = event.get('type', None)
			data = event.get('data', {})
			if etype in self.events:
				data = _decode_description(data.get('description', u''))
				purchase_id = data.get('PurchaseID', u'')
				username = data.get('Username', u'')
				purchase = purchase_history.get_purchase_attempt(purchase_id, username)
				if purchase:
					if etype in ("charge.succeeded") and not purchase.has_succeeded():
						pc = None
						api_key = self.get_api_key(purchase)
						if api_key:
							charges = self.get_charges(purchase_id=purchase_id, start_time=purchase.StartTime, api_key=api_key)
							pc = _create_payment_charge(charges[0]) if charges else None
						notify(store_interfaces.PurchaseAttemptSuccessful(purchase, pc))
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
