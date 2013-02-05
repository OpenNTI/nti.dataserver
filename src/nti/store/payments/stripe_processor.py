#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import time
from datetime import date

from zope import component
from zope import interface
from zope.event import notify

from nti.dataserver.users import User
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.users import interfaces as user_interfaces

from .. import purchase_history
from .stripe_io import StripeIO
from .stripe_io import StripeException
from . import interfaces as pay_interfaces
from .. import interfaces as store_interfaces

import logging
logger = logging.getLogger( __name__ )

@component.adapter(pay_interfaces.IStripeCustomerCreated)
def stripe_customer_created(event):
	def func():
		user = User.get_user(event.username)
		su = pay_interfaces.IStripeCustomer(user)
		su.customer_id = event.customer_id
	component.getUtility(nti_interfaces.IDataserverTransactionRunner)(func)

@component.adapter(pay_interfaces.IStripeCustomerDeleted)
def stripe_customer_deleted(event):
	def func():
		user = User.get_user(event.username)
		su = pay_interfaces.IStripeCustomer(user)
		su.customer_id = None
	component.getUtility(nti_interfaces.IDataserverTransactionRunner)(func)
	
@component.adapter(pay_interfaces.IRegisterStripeToken)
def register_stripe_token(event):
	def func():
		purchase = purchase_history.get_purchase_attempt(event.purchase_id, event.username)
		sp = pay_interfaces.IStripePurchase(purchase)
		sp.TokenID = event.token
	component.getUtility(nti_interfaces.IDataserverTransactionRunner)(func)
	
@component.adapter(pay_interfaces.IRegisterStripeCharge)
def register_stripe_charge(event):
	def func():
		purchase = purchase_history.get_purchase_attempt(event.purchase_id, event.username)
		sp = pay_interfaces.IStripePurchase(purchase)
		sp.ChargeID = event.charge_id
	component.getUtility(nti_interfaces.IDataserverTransactionRunner)(func)
	
@interface.implementer(pay_interfaces.IStripePaymentProcessor)
class _StripePaymentProcessor(StripeIO):
	
	name = 'stripe'

	def create_customer(self, user, api_key=None):
		user = User.get_user(str(user)) if not nti_interfaces.IUser.providedBy(user) else user
		
		profile = user_interfaces.IUserProfile(user)
		email = getattr(profile, 'email', None)
		description = getattr(profile, 'description', None)
	
		customer = self.create_stripe_customer(email, description, api_key)
		notify(pay_interfaces.StripeCustomerCreated(user.username, customer.id))
		
		return customer
	
	def get_or_create_customer(self, user, api_key=None):
		user = User.get_user(str(user)) if not nti_interfaces.IUser.providedBy(user) else user
		adapted = pay_interfaces.IStripeCustomer(user)
		if adapted.customer_id is None:
			customer = self.create_customer(user, api_key)
			result = customer.id
		else:
			result = adapted.customer_id
		return result

	def delete_customer(self, user, api_key=None):
		result = False
		user = User.get_user(str(user)) if not nti_interfaces.IUser.providedBy(user) else user
		adapted = pay_interfaces.IStripeCustomer(user)
		if adapted.customer_id:
			result = self.delete_stripe_customer(customer_id=adapted.customer_id, api_key=api_key)
			notify(pay_interfaces.StripeCustomerDeleted(user.username, adapted.customer_id))
		return result

	def update_customer(self, user, customer=None, api_key=None):
		user = User.get_user(str(user)) if not nti_interfaces.IUser.providedBy(user) else user
		profile = user_interfaces.IUserProfile(user)
		email = getattr(profile, 'email', None)
		description = getattr(profile, 'description', None)
		adapted = pay_interfaces.IStripeCustomer(user)
		if adapted.customer_id:
			return self.update_stripe_customer(	customer=customer,
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
			raise StripeException(charge.failure_message)
		return charge.id
	
	# ---------------------------
	
	def process_purchase(self, purchase_id, username, token, amount, currency, api_key=None):
	
		notify(store_interfaces.PurchaseAttemptStarted(purchase_id, username))
						
		customer_id = self.get_or_create_customer(username, api_key=api_key)
		
		notify(pay_interfaces.RegisterStripeToken(purchase_id, token, username))
		
		descid = "%s,%s,%s" % (username, customer_id, purchase_id)
		try:
			charge_id = self.create_charge(amount, currency, card=token, description=descid, api_key=api_key)
			
			notify(pay_interfaces.RegisterStripeCharge(purchase_id, charge_id, username))
			
			notify(store_interfaces.PurchaseAttemptSuccessful(purchase_id, username))
			
			return charge_id
		except Exception, e:
			message = str(e)
			notify(store_interfaces.PurchaseAttemptFailed(purchase_id, username, message))
			
	def get_charges(self, pid=None, username=None, customer=None, start_time=None, end_time=None, api_key=None):
		result = []
		for c in self.get_stripe_charges(start_time=start_time, end_time=end_time, api_key=api_key):
			desc = c.description
			if (pid and pid in desc) or (username and username in desc) or (customer and customer in desc):
				result.append(c)
		return result
	
	def sync_purchase(self, purchase_id, username, api_key=None):
		charge = None
		user = User.get_user(username)
		purchase = purchase_history.get_purchase_attempt(purchase_id, username)
		sp = pay_interfaces.IStripePurchase(purchase)
		if sp.charge_id:
			charge = self.get_stripe_charge(sp.charge_id, api_key=api_key)
			if charge is None: 
				# if the charge cannot be found it means there was a db error
				# or the charge has been deleted from stripe. 
				message = 'Charge %s/%r for user %s could not be found in Stripe' % (sp.charge_id, purchase.id, user)
				logger.warn(message)
		else:
			start_time = time.mktime(date.fromtimestamp(purchase.StartTime).timetuple())
			charges = self.get_charges(pid=purchase.id, start_time=start_time, api_key=api_key)
			if charges:
				charge = charges[0]
			elif sp.token_id:
				token = self.get_stripe_token(sp.token_id, api_key=api_key)
				if token is None:
					# if the token cannot be found it means there was a db error
					# or the token has been deleted from stripe.
					message = 'Purchase %s/%r for user %s could not found in Stripe' % \
							  (sp.token_id, purchase.id, user)
					logger.warn(message)
					notify(store_interfaces.PurchaseAttemptFailed(purchase_id, username, message))
				elif token.used:
					if not purchase.has_completed():
						# token has been used and no charge has been found, means the transaction failed
						notify(store_interfaces.PurchaseAttemptFailed(purchase_id, username, message))
				elif not purchase.is_pending(): #no charge and unused token
					message = 'Purchase %r for user %s has status issues' % (purchase.id, user)
					logger.warn(message)
					
		if charge:
			if charge.failure_message:
				if not purchase.has_failed():
					notify(store_interfaces.PurchaseAttemptFailed(purchase_id, username, charge.failure_message))
			elif charge.refunded:
				if not purchase.is_refunded():
					notify(store_interfaces.PurchaseAttemptRefunded(purchase_id, username))
			elif charge.paid:
				if not purchase.has_succeeded():
					notify(store_interfaces.PurchaseAttemptSuccessful(purchase_id, username))
				
			notify(store_interfaces.PurchaseAttemptSynced(purchase_id, username))
				
		return charge

				