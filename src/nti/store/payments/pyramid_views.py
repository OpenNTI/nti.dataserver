# -*- coding: utf-8 -*-
"""
Payment pyramid views.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import gevent

from zope import component

from pyramid import httpexceptions as hexc
from pyramid.security import authenticated_userid

from .. import purchase_attempt
from .. import purchase_history
from .. import interfaces as store_interfaces
from .stripe import pyramid_views as stripe_pyramid

class BasePaymentView(object):

	processor = None

	def __init__(self, request):
		self.request = request

	def _valid_amount(self, amount):
		try:
			amount = float(amount)
			return amount > 0
		except:
			return False

	def _valid_int(self, value):
		try:
			value = float(value)
			return value > 0
		except:
			return False

	def __call__(self):
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
		if not token or not self._valid_amount(amount):
			raise hexc.HTTPBadRequest()

		coupon = request.params.get('coupon', None)
		currency = request.params.get('currency', 'USD')
		description = request.params.get('description', None)

		quantity = request.params.get('quantity', None)
		if quantity and not self._valid_int(quantity):
			raise hexc.HTTPBadRequest()

		description = description or "%s's payment for '%r'" % (username, items)

		purchase = purchase_attempt.create_purchase_attempt(items=items, processor=self.processor,
															description=description, quantity=quantity)
		purchase_id = purchase_history.register_purchase_attempt(username, purchase)

		def process_pay():
			manager = component.getUtility(store_interfaces.IPaymentProcessor, name=self.processor)
			manager.process_purchase(purchase_id=purchase_id, username=username, token=token, amount=amount,
									 currency=currency, coupon=coupon)

		gevent.spawn(process_pay)
		return purchase

class StripePaymentView(BasePaymentView):
	processor = 'stripe'

GetStripeConnectKeyView = stripe_pyramid.GetStripeConnectKeyView

