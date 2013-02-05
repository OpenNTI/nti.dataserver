from __future__ import unicode_literals, print_function, absolute_import

import time
from datetime import date

from zope import interface
from zope.event import notify
from zope import lifecycleevent 

from persistent import Persistent

from nti.dataserver.users import User
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.users import interfaces as user_interfaces

from .stripe_io import StripeIO
from .stripe_io import StripeException
from . import interfaces as pay_interfaces
from .. import interfaces as store_interfaces

import logging
logger = logging.getLogger( __name__ )

@interface.implementer(pay_interfaces.IStripePaymentProcessor)
class _StripePaymentProcessor(StripeIO, Persistent):
	
	name = 'stripe'

	def create_customer(self, user, api_key=None):
		user = User.get_user(str(user)) if not nti_interfaces.IUser.providedBy(user) else user
		
		profile = user_interfaces.IUserProfile(user)
		email = getattr(profile, 'email', None)
		description = getattr(profile, 'description', None)
		
		# create and notify
		customer = self.create_stripe_customer(email, description, api_key)
		su = pay_interfaces.IStripeCustomer(user)
		su.customer_id = customer.id
		lifecycleevent.created( su ) 
		
		return su, customer
	
	def get_or_create_customer(self, user, api_key=None):
		customer = None
		user = User.get_user(str(user)) if not nti_interfaces.IUser.providedBy(user) else user
		adapted = pay_interfaces.IStripeCustomer(user)
		if adapted.customer_id is None:
			adapted, customer = self.create_customer(user, api_key)			
		return adapted, customer

	def delete_customer(self, user, api_key=None):
		result = False
		user = User.get_user(str(user)) if not nti_interfaces.IUser.providedBy(user) else user
		adapted = pay_interfaces.IStripeCustomer(user)
		if adapted.customer_id:
			result = self.delete_stripe_customer(customer_id=adapted.customer_id, api_key=api_key)
			lifecycleevent.removed(adapted)
			adapted.customer_id = None
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
	
	def process_purchase(self, user, token, purchase, amount, currency, description, api_key=None):
	
		assert purchase.is_pending()
						
		# we need to create the user first
		user = User.get_user(str(user)) if not nti_interfaces.IUser.providedBy(user) else user
		self.get_or_create_customer(user, api_key=api_key)
		
		sp = pay_interfaces.IStripePurchase(purchase)
		sp.TokenID = token
		
		# set interface for externalization
		interface.alsoProvides( purchase, pay_interfaces.IStripePurchase )
		
		scust = pay_interfaces.IStripeCustomer(user)
		descid = "%s,%s,%s" % (user.username, scust.customer_id, purchase.id)
		try:
			charge_id = self.create_charge(amount, currency, card=token, description=descid, api_key=api_key)
			sp.ChargeID = charge_id
		
			notify(store_interfaces.PurchaseAttemptSuccessful(purchase, user))
			
			# notify items purchased
			notify(pay_interfaces.ItemsPurchased(user, purchase.items, charge_id))
			
			return charge_id
		except Exception, e:
			message = str(e)
			notify(store_interfaces.PurchaseAttemptFailed(purchase, user, message))
			
	def get_charges(self, pid=None, username=None, customer=None, start_time=None, end_time=None, api_key=None):
		result = []
		for c in self.get_stripe_charges(start_time=start_time, end_time=end_time, api_key=api_key):
			desc = c.description
			if (pid and pid in desc) or (username and username in desc) or (customer and customer in desc):
				result.append(c)
		return result
	
	def sync_purchase(self, purchase, user=None, api_key=None):
		charge = None
		sp = pay_interfaces.IStripePurchase(purchase)
		user = User.get_user(str(user)) if not nti_interfaces.IUser.providedBy(user) else user
		if sp.charge_id:
			charge = self.get_stripe_charge(self, sp.charge_id, api_key=api_key)
			if charge is None: 
				# if the charge cannot be found it means there was a db error
				# or the charge has been deleted from stripe. 
				message = 'Charge %s/%r for user %s could not be found in Stripe' % (sp.charge_id, purchase.id, user)
				logger.warn(message)
		else:
			start_time = time.mktime(date.fromtimestamp(purchase.lastModified).timetuple())
			charges = self.get_charges(pid=purchase.pid, start_time=start_time, api_key=api_key)
			if charges:
				charge = charges[0]
			else:
				token = self.get_stripe_token(sp.token_id, api_key=api_key)
				if token is None:
					# if the token cannot be found it means there was a db error
					# or the token has been deleted from stripe.
					message = 'Purchase %s/%r for user %s could not found in Stripe' % \
							  (sp.token_id, purchase.id, user)
					logger.warn(message)
					notify(store_interfaces.PurchaseAttemptFailed(purchase, user, message))
				elif token.used:
					if not purchase.has_completed():
						# token has been used and no charge has been found, means the transaction failed
						notify(store_interfaces.PurchaseAttemptFailed(purchase, user, message))
				elif not purchase.is_pending(): #no charge and unused token
					message = 'Purchase %r for user %s has status issues' % (purchase.id, user)
					logger.warn(message)
					
		if charge:
			if charge.failure_message:
				if purchase.has_succeeded():
					#TODO: Access to items need to be removed
					pass
				elif not purchase.has_failed():
					notify(store_interfaces.PurchaseAttemptFailed(purchase, user, charge.failure_message))
			elif charge.refunded and not purchase.is_refunded():
				notify(store_interfaces.PurchaseAttemptRefunded(purchase, user))
				#TODO: Access to items need to be removed
			elif charge.paid and not purchase.has_succeeded():
				notify(store_interfaces.PurchaseAttemptSuccessful(purchase, user))
				notify(pay_interfaces.ItemsPurchased(user, purchase.items, charge.id))
				
			notify(store_interfaces.PurchaseAttemptSynced(purchase))
				
		return charge

				