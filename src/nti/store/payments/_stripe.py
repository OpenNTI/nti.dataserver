from __future__ import unicode_literals, print_function, absolute_import

import six
import stripe

from zope import interface
from zope.event import notify

from persistent import Persistent

from nti.dataserver.users import User
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.users import interfaces as user_interfaces

from nti.store import transaction
from nti.store import interfaces as store_interfaces
from nti.store.payments import interfaces as pay_interfaces

class StripeException(Exception):
	pass

@interface.implementer(pay_interfaces.IPaymentProcessor)
class _StripePaymentManager(Persistent):
	
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
		
	def create_stripe_charge(self, amount, currency='USD', customer_id=None, card=None, description=None, api_key=None):
		assert customer_id or card
		data = {'amount':amount, 'currency':currency, 'description':description}
		if card:
			data['card'] = card
		else:
			data['customer'] = customer_id
			
		charge = self._do_stripe_operation(stripe.Charge.create, api_key=api_key, **data)
		return charge
	
	# ---------------------------
	
	def _get_customerId(self, user):
		adapted = store_interfaces.ICustomer(user)
		return adapted.getCustomerId(store_interfaces.STRIPE_PROCESSOR)
	
	def create_customer(self, user, api_key=None):
		user = User.get_user(str(user)) if not nti_interfaces.IUser.providedBy(user) else user
		
		profile = user_interfaces.IUserProfile(user)
		email = getattr(profile, 'email', None)
		description = getattr(profile, 'description', None)
		
		# create and notify
		customer = self.create_stripe_customer(email, description, api_key)
		notify(store_interfaces.customerCreated(user, customer.id, store_interfaces.STRIPE_PROCESSOR))
		
		# save customer id
		adapted = store_interfaces.ICustomer(user)
		adapted.setCustomerId(store_interfaces.STRIPE_PROCESSOR, customer.id)
		
		return customer
	
	def get_or_create_customer(self, user, api_key=None):
		customer = None
		user = User.get_user(str(user)) if not nti_interfaces.IUser.providedBy(user) else user
		if self._get_customerId(user) is None:
			customer = self.create_customer(user, api_key)			
		return customer

	def delete_customer(self, user, api_key=None):
		result = False
		user = User.get_user(str(user)) if not nti_interfaces.IUser.providedBy(user) else user
		customer_id = self._get_customerId(user)
		if customer_id:
			result = self.delete_stripe_customer(customer_id=customer_id, api_key=api_key)
			notify(store_interfaces.customerDeleted(user, customer_id, store_interfaces.STRIPE_PROCESSOR))
		return result

	def update_customer(self, user, customer=None, api_key=None):
		user = User.get_user(str(user)) if not nti_interfaces.IUser.providedBy(user) else user
		profile = user_interfaces.IUserProfile(user)
		email = getattr(profile, 'email', None)
		description = getattr(profile, 'description', None)
		customer_id = self._get_customerId(user)
		if customer_id:
			return self.update_stripe_customer(	customer=customer,
												customer_id=customer_id,
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
	
	def process_payment(self, user, token, amount, currency='USD', items=None, description=None, api_key=None):
		
		if items and isinstance(items, six.string_types):
			items = (items,)
			
		# we need to create the user first
		user = User.get_user(str(user)) if not nti_interfaces.IUser.providedBy(user) else user
		self.get_or_create_customer(user, api_key=api_key)
		
		trax = transaction.create_transaction(token, store_interfaces.STRIPE_PROCESSOR)
		notify(store_interfaces.TransactionEvent(user, trax, store_interfaces.TRX_STARTED))
		
		try:
			charge_id = self.create_charge(amount, currency, card=token, description=description, api_key=api_key)
		
			trax.state = store_interfaces.TRX_SUCCESSFUL
			notify(store_interfaces.TransactionCompleted(user, trax, store_interfaces.TRX_SUCCESSFUL, charge_id))
			
			# notify items purchased
			for iid in items:
				notify(pay_interfaces.ItemPurchased(user, iid, charge_id))
			
			return charge_id
		except Exception, e:
			message = str(e)
			trax.failure_message = message
			trax.state = store_interfaces.TRX_FAILED
			notify(store_interfaces.TransactionFailed(user, trax, message))
			
	