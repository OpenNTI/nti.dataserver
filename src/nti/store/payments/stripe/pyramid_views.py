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

from nti.externalization.datastructures import LocatedExternalDict

from . import InvalidStripeCoupon
from . import create_stripe_priceable
from . import interfaces as stripe_interfaces

from nti.store import purchasable
from nti.store import purchase_history
from nti.store import InvalidPurchasable
from nti.store.utils import CaseInsensitiveDict
from nti.store import interfaces as store_interfaces
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

class PricePurchasableWithStripeCouponView(_PostStripeView):

	def price(self, purchasable_id, quantity=None, coupon=None):
		pricer = component.getUtility(store_interfaces.IPurchasablePricer, name="stripe")
		priceable = create_stripe_priceable(ntiid=purchasable_id, quantity=quantity, coupon=coupon)
		result = pricer.price(priceable)
		return result

	def price_purchasable(self, values=None):
		values = values or self.readInput()
		purchasable_id = values.get('purchasableID', u'')
		coupon = values.get('coupon', values.get('couponCode'))

		# check quantity
		quantity = values.get('quantity', 1)
		if not is_valid_pve_int(quantity):
			raise hexc.HTTPBadRequest(detail='invalid quantity')
		quantity = int(quantity)

		try:
			result = self.price(purchasable_id, quantity, coupon)
			return result
		except InvalidStripeCoupon:
			raise hexc.HTTPBadRequest(detail='invalid stripe coupon (%s)' % coupon)
		except InvalidPurchasable:
			raise hexc.HTTPBadRequest(detail='invalid purchasable (%s)' % purchasable_id)

	def __call__(self):
		result = self.price_purchasable()
		return result

class StripePaymentView(_PostStripeView):

	def __call__(self):
		request = self.request
		username = authenticated_userid(request)

		values = self.readInput()
		purchasable_id = values.get('purchasableID')
		if not purchasable_id:
			raise hexc.HTTPBadRequest(detail="No item to purchase specified")

		purchasable = purchasable.get_purchasable(purchasable_id)
		if purchasable is None:
			raise hexc.HTTPBadRequest(detail="Invalid purchasable item")

		# check for any pending purchase for the items being bought
		purchase = purchase_history.get_pending_purchase_for(username, purchasable_id)
		if purchase is not None:
			logger.warn("There is already a pending purchase for item %s" % purchasable_id)
			return LocatedExternalDict({'Items':[purchase], 'Last Modified':purchase.lastModified})

		# gather data
		provider = purchasable.Provider
		stripe_key = component.queryUtility(stripe_interfaces.IStripeConnectKey, provider)
		if not stripe_key:
			raise hexc.HTTPBadRequest(detail="Invalid provider")

		token = values.get('token', None)
		if not token:
			raise hexc.HTTPBadRequest(detail="No token provided")

		amount = values.get('amount', None)
		if not is_valid_amount(amount):
			raise hexc.HTTPBadRequest(detail="Invalid amount")
		amount = float(amount)

		coupon = values.get('coupon', None)
		currency = values.get('currency', 'USD')
		description = values.get('description', None)

		quantity = values.get('quantity', None)
		if quantity is not None and not is_valid_pve_int(quantity):
			raise hexc.HTTPBadRequest(detail="Invalid quantity")
		quantity = int(quantity) if quantity else None

		description = description or "%s's payment for '%r'" % (username, purchasable_id)

		# create purchase
		purchase_id = purchase_history.create_and_register_purchase_attempt(username, items=purchasable_id, processor=self.processor,
																 			description=description, quantity=quantity)
		logger.info("Purchase %s created" % purchase_id)

		# after commit
		manager = component.getUtility(store_interfaces.IPaymentProcessor, name=self.processor)
		def process_purchase():
			logger.info("Processing purchase %s" % purchase_id)
			manager.process_purchase(purchase_id=purchase_id, username=username, token=token, amount=amount,
			 						 currency=currency, coupon=coupon, api_key=stripe_key.PrivateKey)
		transaction.get().addAfterCommitHook(lambda success: success and gevent.spawn(process_purchase))

		# return
		purchase = purchase_history.get_purchase_attempt(purchase_id, username)
		return LocatedExternalDict({'Items':[purchase], 'Last Modified':purchase.lastModified})
