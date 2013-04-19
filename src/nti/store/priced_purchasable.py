# -*- coding: utf-8 -*-
"""
Defines purchase attempt object.

$Id: purchasable.py 18394 2013-04-18 19:27:11Z carlos.sanchez $
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import persistent

from zope import interface
from zope.container import contained as zcontained
from zope.annotation import interfaces as an_interfaces
from zope.mimetype import interfaces as zmime_interfaces
from zope.schema.fieldproperty import FieldPropertyStoredThroughField as FP

from nti.utils.schema import SchemaConfigured

from .utils import MetaStoreObject
from . import interfaces as store_interfaces
from .purchasable_store import get_purchasable

@interface.implementer(store_interfaces.IPricedPurchasable, zmime_interfaces.IContentTypeAware)
class PricedPurchasable(SchemaConfigured):

	__metaclass__ = MetaStoreObject

	NTIID = FP(store_interfaces.IPricedPurchasable['NTIID'])
	PurchaseFee = FP(store_interfaces.IPricedPurchasable['PurchaseFee'])
	PurchasePrice = FP(store_interfaces.IPricedPurchasable['PurchasePrice'])
	NonDiscountedPrice = FP(store_interfaces.IPricedPurchasable['NonDiscountedPrice'])

	@property
	def purchasable(self):
		result = get_purchasable(self.NTIID)
		return result

	@property
	def Currency(self):
		result = getattr(self.purchasable, 'Currency', None)
		return result

	@property
	def Fee(self):
		result = getattr(self.purchasable, 'Fee', None)
		return result

	@property
	def Provider(self):
		result = getattr(self.purchasable, 'Provider', None)
		return result

	@property
	def Amount(self):
		result = getattr(self.purchasable, 'Amount', None)
		return result

	def __str__(self):
		return self.NTIID

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

@interface.implementer(an_interfaces.IAttributeAnnotatable)
class PersistentPricedPurchasable(PricedPurchasable, zcontained.Contained, persistent.Persistent):

	@property
	def id(self):
		return self.NTIID

def create_priced_purchasable(ntiid, purchase_price, purchase_fee=None, non_discouted_price=None):
	purchase_fee = float(purchase_fee) if purchase_fee is not None else None
	non_discouted_price = float(non_discouted_price) if non_discouted_price is not None else None
	result = PricedPurchasable(NTIID=ntiid, PurchasePrice=float(purchase_price), PurchaseFee=purchase_fee,
							   NonDiscountedPrice=non_discouted_price)
	return result
