# -*- coding: utf-8 -*-
"""
Defines purchase attempt object.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import persistent
from zope import interface
from zope.container import contained as zcontained
from zope.annotation import interfaces as an_interfaces
from zope.schema.fieldproperty import FieldPropertyStoredThroughField as FP

from nti.dataserver.datastructures import CreatedModDateTrackingObject

from nti.utils.schema import SchemaConfigured

from . import to_frozenset
from . import interfaces as store_interfaces

@interface.implementer(store_interfaces.IPurchasable)
class BasePurchasable(CreatedModDateTrackingObject, SchemaConfigured):

	NTIID = FP(store_interfaces.IPurchasable['NTIID'])
	Description = FP(store_interfaces.IPurchasable['Description'])
	Amount = FP(store_interfaces.IPurchasable['Amount'])
	Currency = FP(store_interfaces.IPurchasable['Currency'])
	Discountable = FP(store_interfaces.IPurchasable['Discountable'])
	URL = FP(store_interfaces.IPurchasable['URL'])
	Provider = FP(store_interfaces.IPurchasable['Provider'])
	BulkPurchase = FP(store_interfaces.IPurchasable['BulkPurchase'])
	Items = FP(store_interfaces.IPurchasable['Items'])

	def __str__(self):
		return self.NTIID

	def __repr__(self):
		return "%s(%s,%s,%s,%s)" % (self.__class__, self.Description, self.NTIID, self.Currency, self.Amount)

	def __eq__(self, other):
		try:
			return self is other or (store_interfaces.IPurchasable.implementedBy(other)
									 and self.NTIID == other.NTIID)
		except AttributeError:
			return NotImplemented

	def __hash__(self):
		xhash = 47
		xhash ^= hash(self.NTIID)
		return xhash

@interface.implementer(an_interfaces.IAttributeAnnotatable)
class Purchasable(BasePurchasable, zcontained.Contained, persistent.Persistent):

	@property
	def id(self):
		return self.NTIID

def create_purchasable(ntiid, items, provider, title, description, amount, currency=None, url=None,
					   discountable=False, bulk_purchase=True):
	items = to_frozenset(items)
	result = Purchasable(NTIID=ntiid, Provider=provider, Title=title, Items=items,
						 Description=description, Amount=amount, Currency=currency,
						 Discountable=discountable, BulkPurchase=bulk_purchase, URL=url)
	return result
