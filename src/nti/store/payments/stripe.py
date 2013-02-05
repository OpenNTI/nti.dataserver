from __future__ import unicode_literals, print_function, absolute_import

import sys
import time
import stripe
from datetime import date

from zope import interface
from zope import component
from zope.event import notify
from zope import lifecycleevent 
from zope.annotation import factory as an_factory
from zope.container import contained as zcontained

from persistent import Persistent

from nti.dataserver.users import User
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.users import interfaces as user_interfaces

from nti.utils.property import alias

from . import interfaces as pay_interfaces
from .. import interfaces as store_interfaces

import logging
logger = logging.getLogger( __name__ )

class StripeException(Exception):
	pass

@component.adapter(nti_interfaces.IUser)
@interface.implementer( pay_interfaces.IStripeCustomer)
class _StripeCustomer(Persistent):
	
	customer_id = None
	
	@property
	def id(self):
		return self.customer_id
		
def _StripeCustomerFactory(user):
	result = an_factory(_StripeCustomer)(user)
	return result

@component.adapter(store_interfaces.IPurchaseAttempt)
@interface.implementer( pay_interfaces.IStripePurchase)
class _StripePurchase(zcontained.Contained, Persistent):
	
	TokenID = None
	ChargeID = None
	
	@property
	def purchase(self):
		return self.__parent__
	
	token_id = alias('TokenID')
	charge_id = alias('ChargeID')
	
def _StripePurchaseFactory(purchase):
	result = an_factory(_StripePurchase)(purchase)
	return result

@interface.implementer(pay_interfaces.IStripePaymentProcessor)
class _StripePaymentProcessor(Persistent):
	
	name = 'stripe'
	
	def _do_stripe_operation(self,func, *args, **kwargs):
		try:
			result = func(*args, **kwargs)
			return result
		except stripe.CardError, e:
			body = e.json_body
			raise StripeException('%s(%s)' % (body['error'], body['message']))
		except stripe.InvalidRequestError, e:
			raise StripeException(*e.args)
		except stripe.AuthenticationError, e:
			raise StripeException(*e.args)
		except stripe.APIConnectionError, e:
			# Network communication with Stripe failed
			raise StripeException(*e.args)
		except stripe.StripeError, e:
			raise StripeException(*e.args)
		except Exception, e:
			raise StripeException(*e.args)
		
	def create_stripe_customer(self, email, description=None, api_key=None):
		customer = self._do_stripe_operation(stripe.Customer.create, api_key=api_key, email=email, description=description)
		return customer

	def get_stripe_customer(self, customer_id, api_key=None):
		customer = self._do_stripe_operation(stripe.Customer.retrieve, customer_id, api_key)
		return customer
	
	def delete_stripe_customer(self, customer=None, customer_id=None, api_key=None):
		customer = customer or self.get_stripe_customer(customer_id, api_key)
		if customer:
			self._do_stripe_operation(customer.delete)
			return True
		return False
	
	def update_stripe_customer(self, customer_id=None, email=None, description=None, customer=None, api_key=None):
		customer = customer or self.get_stripe_customer(customer_id, api_key)
		if customer:
			customer.email = email
			customer.description = description
			self._do_stripe_operation(customer.save)
			return True
		return False
	
	def create_stripe_token(self, customer_id=None, number=None, exp_month=None, exp_year=None, cvc=None, api_key=None, **kwargs):
		if not customer_id:
			cvc = str(cvc) if cvc else None
			cc = {	'number': number, 'exp_month':exp_month, 
					'exp_year': exp_year, 'cvc': cvc,
					'address_line1': kwargs.get('address_line1', None) or kwargs.get('address', None),
					'address_line2': kwargs.get('address_line2', None) or kwargs.get('address2', None),
					'address_city': kwargs.get('address_city', None) or kwargs.get('city', None),
					'address_state': kwargs.get('address_state', None) or kwargs.get('state', None),
					'address_zip': kwargs.get('address_zip', None) or kwargs.get('zip', None),
					'address_country': kwargs.get('address_country', 'None') or kwargs.get('country', None)
				}
			data = {'card':cc}
		else:
			data = {'customer': customer_id}
		
		token = self._do_stripe_operation(stripe.Token.create, api_key=api_key, **data)
		return token
		
	def get_stripe_token(self, token, api_key=None):
		token = self._do_stripe_operation(stripe.Token.retrieve,token, api_key=api_key)
		return token
	
	def create_stripe_charge(self, amount, currency='USD', customer_id=None, card=None, description=None, api_key=None):
		assert customer_id or card
		data = {'amount':amount, 'currency':currency, 'description':description}
		if card:
			data['card'] = card
		else:
			data['customer'] = customer_id
			
		charge = self._do_stripe_operation(stripe.Charge.create, api_key=api_key, **data)
		return charge
	
	def get_stripe_charge(self, charge_id, api_key=None):
		charge = self._do_stripe_operation(stripe.Charge.retrieve, charge_id, api_key=api_key)
		return charge
	
	def _get_stripe_charges(self, count=10, offset=0, customer=None, api_key=None):
		charges = self._do_stripe_operation(stripe.Charge.all, count=count, offset=offset, 
											customer=customer, api_key=api_key)
		return charges
	
	def get_stripe_charges(self, customer=None, start_time=None, end_time=None, count=50, api_key=None):
		offset = 0
		start_time = int(start_time) if start_time else 0
		end_time = int(end_time) if end_time else sys.maxint
				
		_loop = True
		while _loop:
			charges = self._get_stripe_charges(count=count, offset=offset, customer=customer, api_key=api_key)
			
			if not charges.data:
				_loop = False
			else:
				charges = charges.data
				for c in charges:
					if c.created >= start_time and c.created <= end_time:
						yield c
					
				offset += len(charges)
				
				# since the list of events is ordered desc
				# stop if an old event is not withing the range
				if start_time > charges[-1].created:
					_loop = False
				
	# ---------------------------

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

				