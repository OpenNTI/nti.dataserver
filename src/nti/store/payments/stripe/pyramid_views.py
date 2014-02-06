#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Stripe payment pyramid views.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import simplejson
import transaction

import zope.intid
from zope import component
from zope.event import notify

from pyramid import httpexceptions as hexc
from pyramid.threadlocal import get_current_request

from nti.externalization import integer_strings
from nti.externalization.datastructures import LocatedExternalDict

from nti.ntiids import ntiids

from nti.store import invitations
from nti.store.utils import to_boolean
from nti.store import purchase_history
from nti.store import NTIStoreException
from nti.store import InvalidPurchasable
from nti.store import purchasable as source
from nti.store.utils import is_valid_amount
from nti.store.utils import is_valid_pve_int
from nti.store.utils import is_valid_boolean
from nti.store.utils import raise_field_error
from nti.store import interfaces as store_interfaces

from nti.utils.maps import CaseInsensitiveDict

from . import stripe_purchase
from . import NoSuchStripeCoupon
from . import InvalidStripeCoupon
from . import interfaces as stripe_interfaces

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
		__traceback_info__ = values, self.request.params
		stripe_key = self.get_stripe_connect_key(values)
		manager = component.getUtility(store_interfaces.IPaymentProcessor,
									   name=self.processor)

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
		pricer = component.getUtility(store_interfaces.IPurchasablePricer,
									  name=self.processor)
		priceable = stripe_purchase.create_stripe_priceable(ntiid=purchasable_id,
															quantity=quantity,
															coupon=coupon)
		result = pricer.price(priceable)
		return result

	def price_purchasable(self, values=None):
		values = values or self.readInput()
		purchasable_id = values.get('purchasableID', u'')
		coupon = values.get('coupon', values.get('couponCode'))

		# check quantity
		quantity = values.get('quantity', 1)
		if not is_valid_pve_int(quantity):
			raise_field_error(self.request, "quantity", "invalid quantity")
		quantity = int(quantity)

		try:
			result = self.price(purchasable_id, quantity, coupon)
			return result
		except NoSuchStripeCoupon:
			raise_field_error(self.request, "coupon", "cannot find stripe coupon")
		except InvalidStripeCoupon:
			raise_field_error(self.request, "coupon", "invalid stripe coupon")
		except InvalidPurchasable:
			raise_field_error(self.request, "purchasableID", "invalid purchasable")

	def __call__(self):
		result = self.price_purchasable()
		return result

class StripePaymentView(_PostStripeView):

	def readInput(self, username):
		values = super(StripePaymentView, self).readInput()
		purchasable_id = values.get('purchasableID')
		if not purchasable_id:
			raise_field_error(self.request, 'purchasableID',
							  "No item to purchase specified")

		stripe_key = None
		purchasable = source.get_purchasable(purchasable_id)
		if purchasable is None:
			raise_field_error(self.request, 'purchasableID', "Invalid purchasable item")
		else:
			provider = purchasable.Provider
			stripe_key = \
				component.queryUtility(stripe_interfaces.IStripeConnectKey, provider)
			if not stripe_key:
				raise_field_error(self.request, 'purchasableID',
								  "Invalid purchasable provider")

		token = values.get('token', None)
		if not token:
			raise_field_error(self.request, 'token', "No token provided")

		expected_amount = values.get('amount', values.get('expectedAmount', None))
		if expected_amount is not None and not is_valid_amount(expected_amount):
			raise_field_error(self.request, 'expectedAmount', "Invalid expected amount")
		expected_amount = float(expected_amount) if expected_amount is not None else None

		coupon = values.get('coupon', None)
		description = values.get('description', None)

		quantity = values.get('quantity', None)
		if quantity is not None and not is_valid_pve_int(quantity):
			raise_field_error(self.request, "quantity", "Invalid quantity")
		quantity = int(quantity) if quantity else None

		description = description or "%s's payment for '%r'" % (username, purchasable_id)

		item = stripe_purchase.create_stripe_purchase_item(purchasable_id)
		po = stripe_purchase.create_stripe_purchase_order(item, quantity=quantity,
														  coupon=coupon)

		pa = purchase_history.create_purchase_attempt(po, processor=self.processor)
		return pa, token, stripe_key, expected_amount

	def __call__(self):
		request = self.request

		username = request.authenticated_userid
		purchase_attempt, token, stripe_key, expected_amount = self.readInput(username)

		# check for any pending purchase for the items being bought
		purchase = purchase_history.get_pending_purchase_for(username,
															 purchase_attempt.Items)
		if purchase is not None:
			logger.warn("There is already a pending purchase for item(s) %s",
						list(purchase_attempt.Items))
			return LocatedExternalDict({'Items':[purchase],
										'Last Modified':purchase.lastModified})

		# register purchase
		purchase_id = \
			purchase_history.register_purchase_attempt(purchase_attempt, username)
		logger.info("Purchase attempt (%s) created", purchase_id)

		# after commit
		manager = component.getUtility(store_interfaces.IPaymentProcessor,
									   name=self.processor)
		def process_purchase():
			logger.info("Processing purchase %s", purchase_id)
			manager.process_purchase(purchase_id=purchase_id, username=username,
									 token=token, expected_amount=expected_amount,
									 api_key=stripe_key.PrivateKey,
									 request=request)

		transaction.get().addAfterCommitHook(
							lambda s: s and request.nti_gevent_spawn(process_purchase))

		# return
		purchase = purchase_history.get_purchase_attempt(purchase_id, username)
		return LocatedExternalDict({'Items':[purchase],
									'Last Modified':purchase.lastModified})

class StripeRefundPaymentView(_PostStripeView):

	def readInput(self):
		values = super(StripeRefundPaymentView, self).readInput()
		trax_id = values.get('TransactionID', values.get('transaction_id', None))
		if not trax_id:
			raise_field_error(self.request, 'TransactionID',
							  "No transaction id specified")

		amount = values.get('amount', None)
		if amount is not None and not is_valid_amount(amount):
			raise_field_error(self.request, 'amount', "Invalid amount")
		amount = float(amount) if amount is not None else None

		refund_application_fee = values.get('refundApplicationFee',
								 values.get('refund_application_fee', None))

		if refund_application_fee is not None:
			if not is_valid_boolean(refund_application_fee):
				raise_field_error(self.request, 'refund_application_fee',
								  "Invalid refund application fee")
			refund_application_fee = to_boolean(refund_application_fee)

	def __call__(self):
		request = self.request

		trx_id, amount, refund_application_fee = self.readInput()
		manager = component.getUtility(store_interfaces.IPaymentProcessor,
									   name=self.processor)
		
		try:
			manager.refund_purchase(trx_id, amount=amount,
									refund_application_fee=refund_application_fee,
									request=request)
		except NTIStoreException as e:
			logger.exception("Error while refunding transaction")
			raise hexc.HTTPUnprocessableEntity(detail=str(e))

		# return
		uid = integer_strings.from_external_string(trx_id)
		zope_iids = component.getUtility(zope.intid.IIntIds)
		purchase = zope_iids.queryObject(uid)
		return LocatedExternalDict({'Items':[purchase],
									'Last Modified':purchase.lastModified})

class GeneratePurchaseInvoiceWitStripe(_PostStripeView):

	def _get_purchase(self, key):
		try:
			integer_strings.from_external_string(key)
			purchase = invitations.get_purchase_by_code(key)
		except ValueError:
			if ntiids.is_valid_ntiid_string(key):
				purchase = ntiids.find_object_with_ntiid(key)
			else:
				purchase = None
		return purchase

	def __call__(self):
		values = self.readInput()
		transaction = values.get('transaction', \
								 values.get('purchaseId', values.get('code')))
		if not transaction:
			raise_field_error(self.request, "transaction",
							 "Must specified a valid transaction or purchase code")

		purchase = self._get_purchase(transaction)
		if purchase is None or not store_interfaces.IPurchaseAttempt.providedBy(purchase):
			raise hexc.HTTPNotFound(detail='Transaction not found')
		elif not purchase.has_succeeded():
			raise hexc.HTTPUnprocessableEntity(detail='Purchase was not successfull')

		manager = component.getUtility(store_interfaces.IPaymentProcessor,
									   name=self.processor)
		payment_charge = manager.get_payment_charge(purchase)
			
		notify(store_interfaces.PurchaseAttemptSuccessful(purchase,
														  payment_charge,
														  request=get_current_request()))

		return hexc.HTTPNoContent()
