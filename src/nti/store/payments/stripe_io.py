# -*- coding: utf-8 -*-
"""
Stripe io interface.

$Id: stripe_io.py 15718 2013-02-08 03:30:41Z carlos.sanchez $
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import sys
import stripe

class StripeException(Exception):
	pass

class InvalidStripeRequest(StripeException):
	pass

class StripeIO(object):
	
	def _do_stripe_operation(self,func, *args, **kwargs):
		try:
			result = func(*args, **kwargs)
			return result
		except stripe.CardError, e:
			body = e.json_body
			raise StripeException('%s(%s)' % (body['error'], body['message']))
		except stripe.InvalidRequestError, e:
			raise InvalidStripeRequest(*e.args)
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
		try:
			customer = self._do_stripe_operation(stripe.Customer.retrieve, customer_id, api_key)
			return customer
		except InvalidStripeRequest:
			return None
	
	def delete_stripe_customer(self, customer_id=None, customer=None, api_key=None):
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
		try:
			token = self._do_stripe_operation(stripe.Token.retrieve,token, api_key=api_key)
			return token
		except InvalidStripeRequest:
			return None
	
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
		try:
			charge = self._do_stripe_operation(stripe.Charge.retrieve, charge_id, api_key=api_key)
			return charge
		except InvalidStripeRequest:
			return None
	
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

				