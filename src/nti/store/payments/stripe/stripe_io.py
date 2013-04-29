# -*- coding: utf-8 -*-
"""
Stripe io interface.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import six
import sys
import stripe

from . import StripeException

_marker = object()

class StripeIO(object):

	@classmethod
	def _do_stripe_operation(cls, func, *args, **kwargs):
		try:
			result = func(*args, **kwargs)
			return result
		except stripe.StripeError as e:
			raise e
		except Exception as e:
			raise StripeException(*e.args)

	@classmethod
	def create_stripe_customer(cls, email, description=None, coupon=None, api_key=None):
		customer = cls._do_stripe_operation(stripe.Customer.create, api_key=api_key, email=email,
											coupon=coupon, description=description)
		return customer

	@classmethod
	def get_stripe_customer(cls, customer_id, api_key=None):
		try:
			customer = cls._do_stripe_operation(stripe.Customer.retrieve, customer_id, api_key)
			return customer
		except stripe.InvalidRequestError:
			return None

	@classmethod
	def delete_stripe_customer(cls, customer_id=None, customer=None, api_key=None):
		customer = customer or cls.get_stripe_customer(customer_id, api_key)
		if customer:
			cls._do_stripe_operation(customer.delete)
			return True
		return False

	@classmethod
	def update_stripe_customer(cls, customer, email=_marker, description=_marker, coupon=_marker, api_key=None):
		customer = cls.get_stripe_customer(customer, api_key) if isinstance(customer, six.string_types) else customer
		if customer:
			customer.email = email if email is not _marker else customer.email
			customer.coupon = coupon if coupon is not _marker else customer.coupon
			customer.description = description if description is not _marker else customer.description
			cls._do_stripe_operation(customer.save)
			return True
		return False

	@classmethod
	def create_token(cls, customer_id=None, number=None, exp_month=None, exp_year=None, cvc=None, api_key=None, **kwargs):
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

		token = cls._do_stripe_operation(stripe.Token.create, api_key=api_key, **data)
		return token
	create_stripe_token = create_token

	@classmethod
	def get_stripe_token(cls, token, api_key=None):
		try:
			token = cls._do_stripe_operation(stripe.Token.retrieve, token, api_key=api_key)
			return token
		except stripe.InvalidRequestError:
			return None
	get_token = get_stripe_token

	def create_stripe_charge(self, amount, currency='USD', customer_id=None, card=None, description=None,
							 application_fee=None, api_key=None):
		assert customer_id or card
		data = {'amount':amount, 'currency':currency, 'description':description}
		if card:
			data['card'] = card
		else:
			data['customer'] = customer_id

		if application_fee:
			data['application_fee'] = application_fee
		charge = self._do_stripe_operation(stripe.Charge.create, api_key=api_key, **data)
		return charge
	create_charge = create_stripe_charge

	def get_stripe_charge(self, charge_id, api_key=None):
		try:
			charge = self._do_stripe_operation(stripe.Charge.retrieve, charge_id, api_key=api_key)
			return charge
		except stripe.InvalidRequestError:
			return None
	get_charge = get_stripe_charge

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

	get_charges = get_stripe_charges

	def get_stripe_coupon(self, coupon_code, api_key=None):
		try:
			coupon = self._do_stripe_operation(stripe.Coupon.retrieve, coupon_code, api_key=api_key)
			return coupon
		except stripe.InvalidRequestError:
			return None
