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
from zope.annotation import IAnnotations

from nti.dataserver.users import User
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.users import interfaces as user_interfaces

from . import stripe_io
from ... import payment_charge
from ... import purchase_history
from . import interfaces as stripe_interfaces
from .._processor import _BasePaymentProcessor
from ... import interfaces as store_interfaces

@component.adapter(stripe_interfaces.IStripeCustomerCreated)
def stripe_customer_created(event):
	def func():
		user = User.get_user(event.username)
		su = stripe_interfaces.IStripeCustomer(user)
		su.customer_id = event.customer_id
	component.getUtility(nti_interfaces.IDataserverTransactionRunner)(func)

@component.adapter(stripe_interfaces.IStripeCustomerDeleted)
def stripe_customer_deleted(event):
	def func():
		user = User.get_user(event.username)
		su = stripe_interfaces.IStripeCustomer(user)
		su.customer_id = None
		IAnnotations(user).pop("%s.%s" % (su.__class__.__module__, su.__class__.__name__), None)
	component.getUtility(nti_interfaces.IDataserverTransactionRunner)(func)

@component.adapter(stripe_interfaces.IRegisterStripeToken)
def register_stripe_token(event):
	def func():
		purchase = purchase_history.get_purchase_attempt(event.purchase_id, event.username)
		sp = stripe_interfaces.IStripePurchase(purchase)
		sp.TokenID = event.token
	component.getUtility(nti_interfaces.IDataserverTransactionRunner)(func)

@component.adapter(stripe_interfaces.IRegisterStripeCharge)
def register_stripe_charge(event):
	def func():
		purchase = purchase_history.get_purchase_attempt(event.purchase_id, event.username)
		sp = stripe_interfaces.IStripePurchase(purchase)
		sp.ChargeID = event.charge_id
		user = User.get_user(event.username)
		su = stripe_interfaces.IStripeCustomer(user)
		su.Charges.add(event.charge_id)
	component.getUtility(nti_interfaces.IDataserverTransactionRunner)(func)

def _makenone(s, default=None):
	if isinstance(s, six.string_types) and s == 'None':
		s = default
	return s

def _create_payment_charge(charge):
	amount = charge.amount
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

	def apply_coupon(self, amount, coupon=None, api_key=None):
		coupon = self.get_coupon(coupon, api_key=api_key) if isinstance(coupon, six.string_types) else coupon
		if coupon:
			if coupon.percent_off is not None:
				pcnt = coupon.percent_off / 100.0 if coupon.percent_off > 1 else coupon.percent_off
				amount = amount * (1 - pcnt)
			elif coupon.amount_off is not None:
				amount -= coupon.amount_off
		return max(0, amount)

	def process_purchase(self, purchase_id, username, token, amount, currency, coupon=None, api_key=None):

		purchase = purchase_history.get_purchase_attempt(purchase_id, username)
		if purchase is None:
			raise Exception("Purchase attempt (%s, %s) not found" % (username, purchase_id))

		try:
			if not purchase.is_pending():
				notify(store_interfaces.PurchaseAttemptStarted(purchase_id, username))

			# validate coupon
			coupon = self._get_coupon(coupon, api_key=api_key)
			if coupon is not None and not self.validate_coupon(coupon, api_key=api_key):
				raise ValueError("Invalid coupon")
			amount = self.apply_coupon(amount, coupon, api_key=api_key)
			cents_amount = int(amount * 100.0)  # cents

			# register stripe user and token
			customer_id = self.get_or_create_customer(username, api_key=api_key)
			notify(stripe_interfaces.RegisterStripeToken(purchase_id, username, token))

			# charge card, user description for tracking purposes
			descid = "%s:%s:%s" % (purchase_id, username, customer_id)
			charge = self.create_charge(cents_amount, currency, card=token, description=descid, api_key=api_key)

			notify(stripe_interfaces.RegisterStripeCharge(purchase_id, username, charge.id))

			if charge.paid:
				pc = _create_payment_charge(charge)
				notify(store_interfaces.PurchaseAttemptSuccessful(purchase_id, username, pc))

			return charge.id
		except Exception as e:
			message = str(e)
			notify(store_interfaces.PurchaseAttemptFailed(purchase_id, username, message))

	def get_charges(self, purchase_id=None, username=None, customer=None, start_time=None, end_time=None, api_key=None):
		result = []
		for c in self.get_stripe_charges(start_time=start_time, end_time=end_time, api_key=api_key):
			desc = c.description
			if (purchase_id and purchase_id in desc) or (username and username in desc) or (customer and customer in desc):
				result.append(c)
		return result

	def sync_purchase(self, purchase_id, username, api_key=None):
		user = User.get_user(username)
		purchase = purchase_history.get_purchase_attempt(purchase_id, username)
		if purchase is None:
			logger.error('Purchase %r for user %s could not be found in dB', purchase_id, username)
			return None

		charge = None
		sp = stripe_interfaces.IStripePurchase(purchase)
		if sp.ChargeID:
			charge = self.get_stripe_charge(sp.ChargeID, api_key=api_key)
			if charge is None:
				# if the charge cannot be found it means there was a db error
				# or the charge has been deleted from stripe.
				logger.warn('Charge %s/%r for user %s could not be found in Stripe', sp.ChargeID, purchase_id, user)
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
					message = 'Purchase %s/%r for user %s could not found in Stripe' % (sp.TokenID, purchase_id, username)
					logger.warn(message)
					notify(store_interfaces.PurchaseAttemptFailed(purchase_id, username, message))
				elif token.used:
					if not purchase.has_completed():
						# token has been used and no charge has been found, means the transaction failed
						notify(store_interfaces.PurchaseAttemptFailed(purchase_id, username, message))
				elif not purchase.is_pending():  # no charge and unused token
					logger.warn('Please check status of purchase %r for user %s', purchase_id, username)

		if charge:
			if charge.failure_message:
				if not purchase.has_failed():
					notify(store_interfaces.PurchaseAttemptFailed(purchase_id, username, charge.failure_message))
			elif charge.refunded:
				if not purchase.is_refunded():
					notify(store_interfaces.PurchaseAttemptRefunded(purchase_id, username))
			elif charge.paid:
				if not purchase.has_succeeded():
					pc = _create_payment_charge(charge)
					notify(store_interfaces.PurchaseAttemptSuccessful(purchase_id, username, pc))

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
						amount = data['amount'] / 100.0
						currency = data['currency'].upper()
						notify(store_interfaces.PurchaseAttemptSuccessful(purchase_id, username, amount, currency))
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
