# -*- coding: utf-8 -*-
"""
Stripe payment pyramid views.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import gevent

from zope import component

from pyramid import httpexceptions as hexc
from pyramid.security import authenticated_userid

# from nti.externalization.externalization import toExternalObject
from nti.externalization.datastructures import LocatedExternalDict

from ... import purchase_history
from . import interfaces as stripe_interfaces
from ... import interfaces as store_interfaces
from .. import is_valid_amount, is_valid_pve_int
from ...utils import pyramid_views as util_pyramid_views

class GetStripeConnectKeyView(object):
	processor = 'stripe'

	def __init__(self, request):
		self.request = request

	def get_stripe_connect_key(self):
		params = self.request.params
		keyname = params.get('provider', params.get('alias', u''))
		result = component.queryUtility(stripe_interfaces.IStripeConnectKey, keyname)
		return result

	def __call__(self):
		result = self.get_stripe_connect_key()
		if result is None:
			raise hexc.HTTPNotFound(detail='Provider not found')
		return result

class PricePurchasableWithStripeCouponView(GetStripeConnectKeyView, util_pyramid_views.PricePurchasableView):

	def __call__(self):
		request = self.request
		_, _, amount = self.price_purchasable()
		stripe_key = self.get_stripe_connect_key()
		manager = component.getUtility(store_interfaces.IPaymentProcessor, name=self.processor)

		# stripe defines an 80 sec timeout for http requests
		# at this moment we are to wait for coupon validation
		code = request.params.get('coupon', request.params.get('code', None))
		coupon = manager.get_coupon(code, api_key=stripe_key.PrivateKey)
		validated_coupon = manager.validate_coupon(coupon, api_key=stripe_key.PrivateKey) if coupon is not None else False
		if validated_coupon:
			result = LocatedExternalDict()
			result['Coupon'] = coupon
			result['Provider'] = stripe_key.Alias
			if amount:
				new_amount = manager.apply_coupon(float(amount), coupon)
				result['NewAmount'] = new_amount
			return result

		raise hexc.HTTPNotFound(detail="Invalid coupon")

class StripePaymentView(GetStripeConnectKeyView):

	def __call__(self):
		stripe_key = super(StripePaymentView, self).__call__()

		request = self.request
		username = authenticated_userid(request)
		items = request.params.get('items', request.params.get('nttid', None))

		# check for any pending purchase for the items being bought
		purchase = purchase_history.get_pending_purchase_for(username, items)
		if purchase is not None:
			logger.warn("There is already a pending purchase for item(s) %s" % items)
			return purchase

		token = request.params.get('token', None)
		amount = request.params.get('amount', None)
		if not token or not is_valid_amount(amount):
			raise hexc.HTTPBadRequest(detail="Invalid amount")

		coupon = request.params.get('coupon', None)
		currency = request.params.get('currency', 'USD')
		description = request.params.get('description', None)

		quantity = request.params.get('quantity', None)
		if quantity and not is_valid_pve_int(quantity):
			raise hexc.HTTPBadRequest(detail="Invalid quantity")

		description = description or "%s's payment for '%r'" % (username, items)

		purchase_id = purchase_history.register_purchase_attempt(username, items=items, processor=self.processor,
																 description=description, quantity=quantity)

		def process_pay():
			manager = component.getUtility(store_interfaces.IPaymentProcessor, name=self.processor)
			manager.process_purchase(purchase_id=purchase_id, username=username, token=token, amount=amount,
									 currency=currency, coupon=coupon, api_key=stripe_key.PrivateKey)
		gevent.spawn(process_pay)

		purchase = purchase_history.get_purchase_attempt(purchase_id, username)
		return purchase
