# -*- coding: utf-8 -*-
"""
Stripe purchase functionalilty.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six
import time
import simplejson as json
from datetime import date

from zope import component
from zope import interface
from zope.event import notify

from nti.dataserver.users import User
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.users import interfaces as user_interfaces

from . import stripe_io
from ... import payment_charge
from ... import purchase_history
from ... import purchase_attempt
from .. import _BasePaymentProcessor
from . import interfaces as stripe_interfaces
from ... import interfaces as store_interfaces

def _makenone(s, default=None):
	if isinstance(s, six.string_types) and s == 'None':
		s = default
	return s

def _create_payment_charge(charge):
	amount = charge.amount / 100.0
	currency = charge.currency.upper()
	created = float(charge.created or time.time())
	card = getattr(charge, 'card', None)
	last4 = name = address = None
	if card is not None:
		name = card.name
		last4 = int(card.last4) if card.last4 else None
		address = payment_charge.UserAddress.create(_makenone(card.address_line1),
 													_makenone(card.address_line2),
 													_makenone(card.address_city),
 													_makenone(card.address_state),
 													_makenone(card.address_zip),
 													_makenone(card.address_country))

	result = payment_charge.PaymentCharge(Amount=amount, Currency=currency, Created=created,
										  CardLast4=last4, Address=address, Name=name)
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
		notify(stripe_interfaces.StripeCustomerCreated(user.username, customer.id))

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
			notify(stripe_interfaces.StripeCustomerDeleted(user.username, adapted.customer_id))
		return result

	def update_customer(self, user, customer=None, api_key=None):
		user = User.get_user(str(user)) if not nti_interfaces.IUser.providedBy(user) else user
		profile = user_interfaces.IUserProfile(user)
		email = getattr(profile, 'email', None)
		description = getattr(profile, 'description', None)
		adapted = stripe_interfaces.IStripeCustomer(user)
		if adapted.customer_id:
			return self.update_stripe_customer(customer=customer,
												customer_id=adapted.customer_id,
												email=email,
												description=description,
												api_key=api_key)
		return False

	def create_card_token(self, customer_id=None, number=None, exp_month=None, exp_year=None, cvc=None, api_key=None, **kwargs):
		token = self.create_stripe_token(customer_id, number, exp_month, exp_year, cvc, api_key, **kwargs)
		return token.id

	def create_charge(self, amount, currency='USD', customer_id=None, card=None, description=None, api_key=None):
		charge = self.create_stripe_charge(amount, currency, customer_id, card, description, api_key)
		if charge.failure_message:
			raise stripe_io.StripeException(charge.failure_message)
		return charge

	# ---------------------------

	def _get_coupon(self, coupon, api_key=None):
		result = self.get_coupon(coupon, api_key=api_key) if isinstance(coupon, six.string_types) else coupon
		return result

	def validate_coupon(self, coupon, api_key=None):
		coupon = self.get_coupon(coupon, api_key=api_key) if isinstance(coupon, six.string_types) else coupon
		result = (coupon is not None)
		if result:
			if coupon.duration == u'repeating':
				result = (coupon.duration_in_months is None or coupon.duration_in_months > 0) and \
						 (coupon.max_redemptions is None or coupon.max_redemptions > 0) and \
						 (coupon.redeem_by is None or time.time() <= coupon.redeem_by)
			elif coupon.duration == u'once':
				result = coupon.redeem_by is None or time.time() <= coupon.redeem_by
		return result

	def apply_coupon(self, amount, coupon, api_key=None):
		coupon = self.get_coupon(coupon, api_key=api_key) if isinstance(coupon, six.string_types) else coupon
		if coupon:
			if coupon.percent_off is not None:
				pcnt = coupon.percent_off / 100.0 if coupon.percent_off > 1 else coupon.percent_off
				amount = amount * (1 - pcnt)
			elif coupon.amount_off is not None:
				amount -= coupon.amount_off
		return max(0, amount)

	def process_purchase(self, purchase_id, username, token, amount, currency, coupon=None, api_key=None):
		"""
		Executes the process purchase.
		This function may be called in a greenlet (which cannot be run within a transaction runner)
		"""
		transactionRunner = component.getUtility(nti_interfaces.IDataserverTransactionRunner)

		def start_purchase():
			purchase = purchase_history.get_purchase_attempt(purchase_id, username)
			if not purchase.is_pending():
				notify(store_interfaces.PurchaseAttemptStarted(purchase_id, username))

		def register_stripe_user():
			purchase = purchase_history.get_purchase_attempt(purchase_id, username)
			if not purchase.has_completed():
				logger.error('Getting/Creating Stripe Customer for %s', username)
				customer_id = self.get_or_create_customer(username, api_key=api_key)
				notify(stripe_interfaces.RegisterStripeToken(purchase_id, username, token))
				return customer_id
			return None

		try:
			# start the purchase
			transactionRunner(start_purchase)

			# validate coupon
			if coupon is not None:
				coupon = self._get_coupon(coupon, api_key=api_key)
				if coupon is not None and not self.validate_coupon(coupon, api_key=api_key):
					raise ValueError("Invalid coupon")
				amount = self.apply_coupon(amount, coupon, api_key=api_key)

			# get price amount in cents
			cents_amount = int(amount * 100.0)

			# create a stripe customer
			customer_id = transactionRunner(register_stripe_user)

			# contact stripe
			charge = None
			if customer_id is not None:
				# charge card, user description for tracking purposes
				descid = "%s:%s:%s" % (purchase_id, username, customer_id)
				logger.info('Creating stripe charge for %s', descid)
				charge = self.create_charge(cents_amount, currency, card=token, description=descid, api_key=api_key)

			if charge is not None:
				# register charge
				def register_charge_notify():
					purchase = purchase_history.get_purchase_attempt(purchase_id, username)
					if not purchase.is_pending():
						return

					notify(stripe_interfaces.RegisterStripeCharge(purchase_id, username, charge.id))
					if charge.paid:
						pc = _create_payment_charge(charge)
						notify(store_interfaces.PurchaseAttemptSuccessful(purchase_id, username, pc))
				transactionRunner(register_charge_notify)

			# return charge id
			return charge.id if charge is not None else None
		except Exception as e:
			logger.exception("Cannot complete process purchase for '%s'" % purchase_id)
			# fail purchase
			message = str(e)
			def fail_purchase():
				notify(store_interfaces.PurchaseAttemptFailed(purchase_id, username, message))
			transactionRunner(fail_purchase)

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
		sp = stripe_interfaces.IStripePurchase(purchase)
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
				notify(stripe_interfaces.RegisterStripeCharge(purchase_id, username, charge.id))
			elif sp.TokenID:
				token = self.get_stripe_token(sp.TokenID, api_key=api_key)
				if token is None:
					# if the token cannot be found it means there was a db error
					# or the token has been deleted from stripe.
					message = 'Token %s could not found in Stripe' % sp.TokenID
					logger.warn('Token %s for purchase %r/%s could not found in Stripe', sp.TokenID, purchase_id, username)
					if not purchase.has_completed():
						do_synch = True
						notify(store_interfaces.PurchaseAttemptFailed(purchase_id, username, message))
				elif token.used:
					message = "Token %s has been used and no charge was found" % sp.TokenID
					logger.warn(message)
					if not purchase.has_completed():
						do_synch = True
						notify(store_interfaces.PurchaseAttemptFailed(purchase_id, username, message))
				elif not purchase.is_pending():  # no charge and unused token
					logger.warn('No charge and unused token. Incorrect status for purchase %r/%s', purchase_id, username)

		if charge:
			do_synch = True
			if charge.paid and not purchase.has_succeeded():
				pc = _create_payment_charge(charge)
				notify(store_interfaces.PurchaseAttemptSuccessful(purchase_id, username, pc))
			elif charge.failure_message and not purchase.has_failed():
				notify(store_interfaces.PurchaseAttemptFailed(purchase_id, username, charge.failure_message))
			elif charge.refunded and not purchase.is_refunded():
				notify(store_interfaces.PurchaseAttemptRefunded(purchase_id, username))

		elif time.time() - purchase.StartTime >= 180 and not purchase.has_completed():
			do_synch = True
			message = message or "Failed purchase after expiration time"
			notify(store_interfaces.PurchaseAttemptFailed(purchase_id, username, message))

		if do_synch:
			notify(store_interfaces.PurchaseAttemptSynced(purchase_id, username))
		return charge

	def process_event(self, body):
		try:
			event = json.loads(body) if isinstance(body, six.string_types) else body
			etype = event.get('type', None)
			data = event.get('data', {})
			if etype in self.events:
				tracks = data.get('description', u'').split(":")
				purchase_id = tracks[0] if len(tracks) >= 2 else u''
				username = tracks[1] if len(tracks) >= 2 else u''
				purchase = purchase_history.get_purchase_attempt(purchase_id, username)
				if purchase:
					if etype in ("charge.succeeded") and not purchase.has_succeeded():
						pc = None
						api_key = self.get_api_key(purchase)
						if api_key:
							charges = self.get_charges(purchase_id=purchase_id, start_time=purchase.StartTime, api_key=api_key)
							pc = _create_payment_charge(charges[0]) if charges else None
						notify(store_interfaces.PurchaseAttemptSuccessful(purchase_id, username, pc))
					elif etype in ("charge.refunded") and not purchase.is_refunded():
						notify(store_interfaces.PurchaseAttemptRefunded(purchase_id, username))
					elif etype in ("charge.failed") and not purchase.has_failed():
						notify(store_interfaces.PurchaseAttemptFailed(purchase_id, username))
					elif etype in ("charge.dispute.created", "charge.dispute.updated") and not purchase.is_disputed():
						notify(store_interfaces.PurchaseAttemptDisputed(purchase_id, username))
			else:
				logger.debug('Unhandled event type (%s)' % etype)
			return True
		except Exception:
			logger.exception('Error processing stripe event (webhook)')
			return False
