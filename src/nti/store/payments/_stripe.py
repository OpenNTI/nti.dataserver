from __future__ import unicode_literals, print_function, absolute_import

import re
import stripe

from zope import component
from zope import interface

from persistent.mapping import PersistentMapping

from nti.dataserver.users import User
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.users import interfaces as user_interfaces

from nti.store.payments import interfaces as pay_interfaces

class StripeException(Exception):
	pass

@component.adapter(nti_interfaces.IEntity)
@interface.implementer( pay_interfaces.IStripeCustomer)
class StripeCustomer(interface.Interface):
	
	_purchases = None
	customer_id = None
	active_card = None

	def __init__(self, customer_id=None, active_card=None):
		if customer_id:
			self.customer_id = customer_id
		if active_card:
			self.active_card = active_card
		
	@property
	def id(self):
		return self.customer_id
	
	@property
	def purchases(self):
		if self._purchases is None:
			self._purchases = PersistentMapping()
		return self._purchases
	
	def add_purchase(self, purchase_id, item_id):
		self.purchases[purchase_id] = item_id
		
	def clear_purchases(self):
		self.purchases().clear()
		
	def clear(self):
		self.active_card = None
		self.customer_id = None
		self.clear_purchases()

def create_stripe_customer(user, api_key=None):
	user = User.get_user(str(user)) if not nti_interfaces.IUser.providedBy(user) else user
	profile = user_interfaces.IUserProfile(user)
	email = getattr(profile, 'email', None)
	description = getattr(profile, 'description', None)
	try:
		customer = stripe.Customer.create(api_key=api_key, email=email, description=description)
		return customer
	except Exception, e:
		raise StripeException(*e.args)

def get_or_create_customer(user, api_key=None):
	user = User.get_user(str(user)) if not nti_interfaces.IUser.providedBy(user) else user
	adapted = pay_interfaces.IStripeCustomer(user)
	if adapted.customer_id is None:
		customer = create_stripe_customer(user)
		adapted.customer_id = customer.id
	return adapted

def get_stripe_customer(customer_id, api_key=None):
	try:
		customer = stripe.Customer.retrieve(id, api_key)
		return customer
	except Exception, e:
		raise StripeException(*e.args)
	
def delete_stripe_customer(customer_id, api_key=None):
	customer = get_stripe_customer(customer_id, api_key)
	try:
		if customer:
			customer.delete()
			return True
		return False
	except Exception, e:
		raise StripeException(*e.args)

def delete_customer(user, card=None, api_key=None):
	result = False
	user = User.get_user(str(user)) if not nti_interfaces.IUser.providedBy(user) else user
	adapted = pay_interfaces.IStripeCustomer(user)
	if adapted.customer_id:
		result = delete_stripe_customer(adapted.customer_id, api_key)
		adapted.clear()
	return result

def update_stripe_customer(customer_id, card=None, email=None, description=None, api_key=None):
	customer = get_stripe_customer(customer_id, api_key)
	if customer:
		customer.card = card
		customer.email = email
		customer.description = description
		try:
			customer.save() 
			return True
		except Exception, e:
			raise StripeException(*e.args)
	return False

def update_customer(user, card=None, api_key=None):
	user = User.get_user(str(user)) if not nti_interfaces.IUser.providedBy(user) else user
	profile = user_interfaces.IUserProfile(user)
	email = getattr(profile, 'email', None)
	description = getattr(profile, 'description', None)
	if profile.customer_id:
		return update_stripe_customer(	profile.customer_id, 
										card=card,
										email=email,
										description=description,
										api_key=api_key)
	return False

def create_stripe_token(customer_id=None, number=None, exp_month=None, exp_year=None, cvc=None, api_key=None, **kwargs):
	if not customer_id:
		number = re.sub("[^0-9]", "", str(number))
		cvc = str(cvc) if cvc else None
		cc = {	'number': number, 'exp_month':exp_month, 
				'exp_year': exp_year, 'cvc': cvc,
				'address_line1': kwargs.get('address_line1', None) or kwargs.get('address', None),
				'address_line2': kwargs.get('address_line2', None) or kwargs.get('address2', None),
				'address_city': kwargs.get('address_city', None) or kwargs.get('city', None),
				'address_zip': kwargs.get('address_zip', None) or kwargs.get('zip', None),
				'address_country': kwargs.get('address_country', None) or kwargs.get('country', None)
			}
		data = {'card':cc}
	else:
		data = {'customer': customer_id}
	
	try:
		token = stripe.Token.create(api_key=api_key, **data)
		return token
	except Exception, e:
		raise StripeException(*e.args)

def create_card_token(customer_id=None, number=None, exp_month=None, exp_year=None, cvc=None, api_key=None, **kwargs):
	token = create_stripe_token(locals())
	return token.id

def create_stripe_charge(amount, currency='USD', customer_id=None, card=None, description=None, api_key=None):
	assert customer_id or card
	data = {'amount':amount, 'currency':currency, 'description':description}
	if card:
		data['card'] = card
	else:
		data['customer'] = customer_id
		
	try:
		charge = stripe.Charge.create(api_key=api_key, **data)
		return charge
	except Exception, e:
		raise StripeException(*e.args)

def create_charge(amount, currency='USD', customer_id=None, card=None, description=None, api_key=None):
	charge = create_stripe_charge(locals())
	if charge.failure_message:
		raise StripeException(charge.failure_message)
	return charge.id
