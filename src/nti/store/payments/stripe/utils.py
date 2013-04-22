# -*- coding: utf-8 -*-
"""
Stripe utilities.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import six

from zope import component

from . import InvalidStripeCoupon
from . import interfaces as stripe_interfaces
from ... import interfaces as store_interfaces
from .stripe_purchase import StripePricedPurchasable

from nti.store import PricingException
from nti.store.pricing import create_priced_items, DefaultPurchasablePricer

def makenone(s, default=None):
	if isinstance(s, six.string_types):
		s = default if s == 'None' else unicode(s)
	return s

class StripePurchasablePricer(DefaultPurchasablePricer):

	processor = "stripe"

	def get_coupon(self, coupon=None, api_key=None):
		manager = component.getUtility(store_interfaces.IPaymentProcessor, name=self.processor)
		if coupon is not None and api_key:
			# stripe defines an 80 sec timeout for http requests
			# at this moment we are to wait for coupon validation
			if isinstance(coupon, six.string_types):
				coupon = manager.get_coupon(coupon, api_key=api_key)
			if coupon is not None:
				validated_coupon = manager.validate_coupon(coupon, api_key=api_key)
				if not validated_coupon:
					raise InvalidStripeCoupon()
		return coupon

	def price(self, priceable):
		priced = super(StripePurchasablePricer, self).price(priceable)
		priced = StripePricedPurchasable.copy(priced)
		coupon = getattr(priceable, 'Coupon', None)

		manager = component.getUtility(store_interfaces.IPaymentProcessor, name=self.processor)
		stripe_key = component.queryUtility(stripe_interfaces.IStripeConnectKey, priced.Provider)

		purchase_price = priced.PurchasePrice

		if coupon is not None and stripe_key:
			priced.Coupon = self.get_coupon(coupon, stripe_key.PrivateKey)
			if priced.Coupon is not None:
				priced.NonDiscountedPrice = purchase_price
				purchase_price = manager.apply_coupon(purchase_price, priced.Coupon)
				priced.PurchasePrice = purchase_price
				priced.PurchaseFee = self.calc_fee(purchase_price, priceable.Fee)
		return priced

	def evaluate(self, priceables):
		providers = set()
		currencies = set()
		result = create_priced_items(non_discounted_price=0.0)
		for priceable in priceables:
			currencies.add(priceable.Currency)
			providers.add(priceable.Provider)
			priced = self.price(priceable)
			result.PricedList.append(priced)
			result.TotalPurchaseFee += priced.PurchaseFee
			result.TotalPurchasePrice += priced.PurchasePrice
			result.TotalNonDiscountedPrice += priced.NonDiscountedPrice or priced.PurchasePrice

		if len(currencies) != 1:
			raise PricingException("Multi-Currency pricing is not supported")
		result.Currency = currencies.pop()

		# apply coupon at the 'order' level
		coupon = getattr(priceables, 'Coupon', None)
		if coupon is not None:
			if len(providers) != 1:
				raise PricingException("Multi-Provider coupon purchase is not supported")

			provider = providers.pop()
			stripe_key = component.queryUtility(stripe_interfaces.IStripeConnectKey, provider)
			coupon = self.get_coupon(coupon, stripe_key.PrivateKey)
			manager = component.getUtility(store_interfaces.IPaymentProcessor, name=self.processor)
			if coupon is not None:
				result.NonDiscountedPrice = result.TotalPurchasePrice
				purchase_price = manager.apply_coupon(result.TotalPurchasePrice, coupon)
				result.TotalPurchasePrice = purchase_price
				result.TotalPurchaseFee = self.calc_fee(purchase_price, priceable.Fee)

		return result
