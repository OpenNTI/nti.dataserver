# -*- coding: utf-8 -*-
"""
Defines priceable object.

$Id: purchasable.py 18394 2013-04-18 19:27:11Z carlos.sanchez $
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import interface
from zope.mimetype import interfaces as zmime_interfaces
from zope.schema.fieldproperty import FieldPropertyStoredThroughField as FP

from nti.utils.schema import SchemaConfigured

from . import InvalidPurchasable
from .purchasable import get_purchasable
from . import interfaces as store_interfaces
from .utils import MetaStoreObject, to_collection

@interface.implementer(store_interfaces.IPriceable, zmime_interfaces.IContentTypeAware)
class Priceable(SchemaConfigured):

	__metaclass__ = MetaStoreObject

	NTIID = FP(store_interfaces.IPriceable['NTIID'])
	Quantity = FP(store_interfaces.IPriceable['Quantity'])

	@property
	def purchasable(self):
		result = get_purchasable(self.NTIID)
		return result

	@property
	def Currency(self):
		result = getattr(self.purchasable, 'Currency', None)
		return result

	@property
	def Provider(self):
		result = getattr(self.purchasable, 'Provider', None)
		return result

	@property
	def Amount(self):
		result = getattr(self.purchasable, 'Amount', None)
		return result

	@property
	def Fee(self):
		result = getattr(self.purchasable, 'Fee', None)
		return result

	def __str__(self):
		return self.NTIID

	def __repr__(self):
		return "%s(%s)" % (self.__class__.__name__, self.NTIID)

	def __eq__(self, other):
		try:
			return self is other or (store_interfaces.IPriceable.providedBy(other)
									 and self.NTIID == other.NTIID)
		except AttributeError:
			return NotImplemented

	def __hash__(self):
		xhash = 47
		xhash ^= hash(self.NTIID)
		return xhash

def create_priceable(ntiid, quantity=1):
	quantity = 1 if quantity is None else int(quantity)
	result = Priceable(NTIID=unicode(ntiid), Quantity=quantity)
	return result

@interface.implementer(store_interfaces.IPricedPurchasable, zmime_interfaces.IContentTypeAware)
class PricedPurchasable(Priceable):

	__metaclass__ = MetaStoreObject

	PurchaseFee = FP(store_interfaces.IPricedPurchasable['PurchaseFee'])
	PurchasePrice = FP(store_interfaces.IPricedPurchasable['PurchasePrice'])
	NonDiscountedPrice = FP(store_interfaces.IPricedPurchasable['NonDiscountedPrice'])

	def __repr__(self):
		return "%s(%s,%s,%s)" % (self.__class__.__name__, self.NTIID, self.Currency, self.PurchasePrice)

	def __eq__(self, other):
		try:
			return self is other or (store_interfaces.IPricedPurchasable.providedBy(other)
									 and self.NTIID == other.NTIID)
		except AttributeError:
			return NotImplemented

	def __hash__(self):
		xhash = 47
		xhash ^= hash(self.NTIID)
		return xhash

def create_priced_purchasable(ntiid, purchase_price, purchase_fee=None, non_discounted_price=None, quantity=1):
	quantity = 1 if quantity is None else int(quantity)
	purchase_fee = float(purchase_fee) if purchase_fee is not None else None
	non_discounted_price = float(non_discounted_price) if non_discounted_price is not None else None
	result = PricedPurchasable(NTIID=unicode(ntiid), PurchasePrice=float(purchase_price), PurchaseFee=purchase_fee,
							   NonDiscountedPrice=non_discounted_price, Quantity=quantity)
	return result


@interface.implementer(store_interfaces.IPricingResults, zmime_interfaces.IContentTypeAware)
class PrincingResults(SchemaConfigured):

	__metaclass__ = MetaStoreObject

	PricedList = FP(store_interfaces.IPricingResults['PricedList'])
	TotalPurchaseFee = FP(store_interfaces.IPricingResults['TotalPurchaseFee'])
	TotalPurchasePrice = FP(store_interfaces.IPricingResults['TotalPurchasePrice'])
	TotalNonDiscountedPrice = FP(store_interfaces.IPricingResults['TotalNonDiscountedPrice'])

def create_pricing_results(priced_list=None, purchase_price=0.0, purchase_fee=0.0, non_discounted_price=None):
	priced_list = list() if priced_list is None else priced_list
	purchase_fee = float(purchase_fee) if purchase_fee is not None else None
	non_discounted_price = float(non_discounted_price) if non_discounted_price is not None else None
	result = PrincingResults(PricedList=priced_list, TotalPurchasePrice=purchase_price, TotalPurchaseFee=purchase_fee,
							 TotalNonDiscountedPrice=non_discounted_price)
	return result

@interface.implementer(store_interfaces.IPurchasablePricer)
class DefaultPurchasablePricer(object):

	def calc_fee(self, amount, fee):
		fee_amount = 0
		if fee is not None:
			pct = fee / 100.0 if fee >= 1 else fee
			fee_amount = amount * pct
		return fee_amount

	def price(self, priceable):
		quantity = priceable.Quantity or 1
		purchasable = priceable.purchasable
		if purchasable is None:
			raise InvalidPurchasable("must specify a valid purchasable")

		amount = purchasable.Amount
		new_amount = amount * quantity

		fee_amount = self.calc_fee(new_amount, purchasable.Fee)
		result = create_priced_purchasable(ntiid=purchasable.NTIID,
										   purchase_price=new_amount,
										   purchase_fee=fee_amount,
										   quantity=quantity)
		return result

	def evaluate(self, priceables):
		priceables = to_collection(priceables)
		result = create_pricing_results()
		for priceable in priceables:
			priced = self.price(priceable)
			result.PricedList.append(priced)
			result.TotalPurchaseFee += priced.PurchaseFee
			result.TotalPurchasePrice += priced.PurchasePrice
		return result
