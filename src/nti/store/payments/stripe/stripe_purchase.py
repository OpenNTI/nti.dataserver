# -*- coding: utf-8 -*-
"""
Defines stripe payment object.

$Id: purchasable.py 18394 2013-04-18 19:27:11Z carlos.sanchez $
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import interface
from zope.schema.fieldproperty import FieldPropertyStoredThroughField as FP

from ... import pricing
from ... import priceable
from ... import purchase_order
from . import interfaces as stripe_interfaces

@interface.implementer(stripe_interfaces.IStripePriceable)
class StripePriceable(priceable.Priceable):

	Coupon = FP(stripe_interfaces.IStripePriceable['Coupon'])

	def __eq__(self, other):
		try:
			return super(StripePriceable, self).__eq__(other) and self.Coupon == other.Coupon
		except AttributeError:
			return NotImplemented

	def __hash__(self):
		xhash = super(StripePriceable, self).__hash__()
		xhash ^= hash(self.Coupon)
		return xhash

def create_stripe_priceable(ntiid, quantity=None, coupon=None):
	quantity = 1 if quantity is None else int(quantity)
	result = StripePriceable(NTIID=unicode(ntiid), Quantity=quantity, Coupon=coupon)
	return result

@interface.implementer(stripe_interfaces.IStripePricedItem)
class StripePricedItem(pricing.PricedItem):

	Coupon = FP(stripe_interfaces.IStripePricedItem['Coupon'])

	@classmethod
	def copy(cls, priced):
		result = cls(NTIID=priced.NTIID,
					 Quantity=priced.Quantity,
					 PurchaseFee=priced.PurchaseFee,
					 PurchasePrice=priced.PurchasePrice,
					 NonDiscountedPrice=priced.NonDiscountedPrice)
		result.Coupon = getattr(priced, 'Coupon', None)
		return result

	def __eq__(self, other):
		try:
			return super(StripePricedItem, self).__eq__(other) and self.Coupon == other.Coupon
		except AttributeError:
			return NotImplemented

	def __hash__(self):
		xhash = super(StripePricedItem, self).__hash__()
		xhash ^= hash(self.Coupon)
		return xhash

# alias bwc
class StripePricedPurchasable(StripePricedItem):
	pass

@interface.implementer(stripe_interfaces.IStripePurchaseItem)
class StripePurchaseItem(StripePriceable, purchase_order.PurchaseItem):
	pass

@interface.implementer(stripe_interfaces.IStripePurchaseOrder)
class StripePurchaseOrder(purchase_order.PurchaseOrder):

	Coupon = FP(stripe_interfaces.IStripePurchaseOrder['Coupon'])  # overide items coupon

	def __eq__(self, other):
		try:
			return super(StripePurchaseOrder, self).__eq__(other) and self.Coupon == other.Coupon
		except AttributeError:
			return NotImplemented

	def __hash__(self):
		xhash = super(StripePurchaseOrder, self).__hash__()
		xhash ^= hash(self.Coupon)
		return xhash
