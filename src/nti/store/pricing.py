# -*- coding: utf-8 -*-
"""
Defines purchase attempt object.

$Id: purchasable.py 18394 2013-04-18 19:27:11Z carlos.sanchez $
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import interface
from zope.mimetype import interfaces as zmime_interfaces
from zope.schema.fieldproperty import FieldPropertyStoredThroughField as FP

from nti.utils.schema import SchemaConfigured

from . import InvalidPurchasable
from .utils import to_collection
from .utils import MetaStoreObject
from . import interfaces as store_interfaces
from .purchasable_store import get_purchasable

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

def create_priced_purchasable(ntiid, purchase_price, purchase_fee=None, non_discounted_price=None,
							  quantity=1):
	quantity = 1 if quantity is None else int(quantity)
	purchase_fee = float(purchase_fee) if purchase_fee is not None else None
	non_discouted_price = float(non_discounted_price) if non_discounted_price is not None else None
	result = PricedPurchasable(NTIID=unicode(ntiid), PurchasePrice=float(purchase_price), PurchaseFee=purchase_fee,
							   NonDiscountedPrice=non_discouted_price, Quantity=quantity)
	return result


@interface.implementer(store_interfaces.IPricingResults, zmime_interfaces.IContentTypeAware)
class PrincingResults(SchemaConfigured):

	__metaclass__ = MetaStoreObject

	TotalPurchaseFee = FP(store_interfaces.IPricedPurchasable['PurchaseFee'])
	TotalPurchasePrice = FP(store_interfaces.IPricedPurchasable['PurchasePrice'])
	TotalNonDiscountedPrice = FP(store_interfaces.IPricedPurchasable['NonDiscountedPrice'])

	def __init__(self, *args, **kwargs):
		super(PrincingResults, self).__init__(*args, **kwargs)
		self.PricedList = list()

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

		# price
		total_fee = 0
		total_amount = 0
		result = PrincingResults()
		for priceable in priceables:
			priced = self.price(priceable)
			result.PricedList.append(priced)
			total_fee += priced.PurchaseFee
			total_amount += priced.PurchasePrice

		# set totals
		result.TotalPurchaseFee = total_fee
		result.TotalPurchasePrice = total_amount
		return result
