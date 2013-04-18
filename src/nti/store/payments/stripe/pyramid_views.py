# -*- coding: utf-8 -*-
"""
Stripe payment pyramid views.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import gevent
import simplejson
import transaction

from zope import component

from pyramid import httpexceptions as hexc
from pyramid.security import authenticated_userid

from nti.dataserver import interfaces as nti_interfaces

from nti.externalization.datastructures import LocatedExternalDict

from nti.store import purchase_history
from . import interfaces as stripe_interfaces
from nti.store.utils import CaseInsensitiveDict
from nti.store import interfaces as store_interfaces
from nti.store.utils import pyramid_views as util_pyramid_views
from nti.store.payments import is_valid_amount, is_valid_pve_int

class _BaseStripeView(object):
	processor = 'stripe'

	def __init__(self, request):
		self.request = request

	def get_stripe_connect_key(self, params=None):
		params = params if params else self.request.params
		keyname = params.get('provider', params.get('Provider', u''))
		result = component.queryUtility(stripe_interfaces.IStripeConnectKey, keyname)
		return result

class _PostStripeView(_BaseStripeView):

	def readInput(self):
		request = self.request
		values = simplejson.loads(unicode(request.body, request.charset))
		return CaseInsensitiveDict(**values)

class GetStripeConnectKeyView(_BaseStripeView):

	def __call__(self):
		result = self.get_stripe_connect_key()
		if result is None:
			raise hexc.HTTPNotFound(detail='Provider not found')
		return result

class CreateStripeTokenView(_PostStripeView):

	def __call__(self):
		values = self.readInput()
		stripe_key = self.get_stripe_connect_key(values)
		manager = component.getUtility(store_interfaces.IPaymentProcessor, name=self.processor)

		params = {'api_key':stripe_key.PrivateKey}

		customer_id = values.get('customerID', values.get('customer_id', None))
		if not customer_id:
			required = (('cvc', 'cvc', ''),
						('exp_year', 'expYear', 'exp_year'),
						('exp_month', 'expMonth', 'exp_month'),
						('number', 'CC', 'number'))

			for k, p, a in required:
				value = values.get(p, values.get(a, None))
				if not value:
					raise hexc.HTTPBadRequest(detail='Invalid %s value' % p)
				params[k] = str(value)
		else:
			params['customer_id'] = customer_id

		# optional
		optional = (('address_line1', 'address_line1', 'address'),
					('address_line2', 'address_line2', ''),
					('address_city', 'address_city', 'city'),
					('address_state', 'address_state', 'state'),
					('address_zip', 'address_zip', 'zip'),
					('address_country', 'address_country', 'country'))
		for k, p, a in optional:
			value = values.get(p, values.get(a, None))
			if value:
				params[k] = str(value)

		token = manager.create_token(**params)
		return LocatedExternalDict(Token=token.id)

class PricePurchasableWithStripeCouponView(_PostStripeView, util_pyramid_views.PricePurchasableView):

	def __call__(self):
		values = self.price_purchasable()
		new_amount = values['NewAmount']
		stripe_key = self.get_stripe_connect_key(values)
		manager = component.getUtility(store_interfaces.IPaymentProcessor, name=self.processor)

		coupon = None
		result = LocatedExternalDict()
		result['Amount'] = values['Amount']
		result['NonDiscountedAmount'] = new_amount
		code = values.get('coupon', None)
		if code is not None and stripe_key:
			# stripe defines an 80 sec timeout for http requests
			# at this moment we are to wait for coupon validation
			coupon = manager.get_coupon(code, api_key=stripe_key.PrivateKey)
			if coupon is not None:
				validated_coupon = manager.validate_coupon(coupon, api_key=stripe_key.PrivateKey)
				if validated_coupon:
					result['Provider'] = stripe_key.Alias
				else:
					raise hexc.HTTPClientError(detail="Invalid coupon")
			result['Coupon'] = coupon

		new_amount = float(new_amount)
		if coupon is not None:
			new_amount = manager.apply_coupon(new_amount, coupon)
			result['DiscountedAmount'] = new_amount
		return result

class StripePaymentView(_PostStripeView):

	def __call__(self):
		request = self.request

		# read input
		values = self.readInput()
		username = authenticated_userid(request)
		stripe_key = self.get_stripe_connect_key(values)

		# get items to purchase
		items = values.get('purchasableID', values.get('PurchasableID', None))
		if not items:
			items = values.get('items', values.get('Items', None))
		if not items:
			raise hexc.HTTPBadRequest(detail="No item(s) to purchase")

		# check for any pending purchase for the items being bought
		purchase = purchase_history.get_pending_purchase_for(username, items)
		if purchase is not None:
			logger.warn("There is already a pending purchase for item(s) %s" % items)
			return purchase

		token = values.get('token', values.get('Token', None))
		if not token:
			raise hexc.HTTPBadRequest(detail="No token provided")

		amount = values.get('amount', values.get('Amount', None))
		if not is_valid_amount(amount):
			raise hexc.HTTPBadRequest(detail="Invalid amount")

		coupon = values.get('coupon', values.get('Coupon', None))
		currency = values.get('currency', values.get('Currency', 'USD'))
		description = values.get('description', values.get('Description', None))

		quantity = values.get('quantity', values.get('Quantity', None))
		if quantity is not None and not is_valid_pve_int(quantity):
			raise hexc.HTTPBadRequest(detail="Invalid quantity")

		description = description or "%s's payment for '%r'" % (username, items)

		purchase_id = purchase_history.register_purchase_attempt(username, items=items, processor=self.processor,
																 description=description, quantity=quantity)
		logger.info("Purchase %s created" % purchase_id)

		# after commit
		def process_purchase():
			logger.info("Processing purchase %s" % purchase_id)
			manager = component.getUtility(store_interfaces.IPaymentProcessor, name=self.processor)
			manager.process_purchase(purchase_id=purchase_id, username=username, token=token, amount=amount,
									 currency=currency, coupon=coupon, api_key=stripe_key.PrivateKey)

		def process_pay():
			component.getUtility(nti_interfaces.IDataserverTransactionRunner)(process_purchase)

		transaction.get().addAfterCommitHook(lambda success: success and gevent.spawn(process_purchase))

		purchase = purchase_history.get_purchase_attempt(purchase_id, username)
		return LocatedExternalDict({'Items':[purchase], 'Last Modified':purchase.lastModified})
