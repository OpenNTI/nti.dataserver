# -*- coding: utf-8 -*-
"""
Defines purchase order.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import collections

from zope import interface
from zope.annotation import interfaces as an_interfaces
from zope.schema.fieldproperty import FieldPropertyStoredThroughField as FP

from nti.utils.schema import SchemaConfigured

from . priceable import Priceable
from .utils import MetaStoreObject
from . import interfaces as store_interfaces

@interface.implementer(store_interfaces.IPurchaseItem)
class PurchaseItem(Priceable):
	__metaclass__ = MetaStoreObject

def create_purchase_item(ntiid, quantity=1, cls=PurchaseItem):
	quantity = 1 if quantity is None else int(quantity)
	result = cls(NTIID=unicode(ntiid), Quantity=quantity)
	return result

@interface.implementer(store_interfaces.IPurchaseOrder, an_interfaces.IAttributeAnnotatable)
class PurchaseOrder(SchemaConfigured):

	__metaclass__ = MetaStoreObject

	Items = FP(store_interfaces.IPurchaseOrder['Items'])
	Quantity = FP(store_interfaces.IPurchaseOrder['Quantity'])  # override items quantity

	def __repr__(self):
		return "%s(%s)" % (self.__class__.__name__, self.Items, self.Quantity)

	def __getitem__(self, index):
		return self.Items[index]

	def __iter__(self):
		return iter(self.Items)

	def __eq__(self, other):
		try:
			return self is other or (self.Items == other.Items
									 and self.Quantity == other.Quantity)
		except AttributeError:
			return NotImplemented

	def __hash__(self):
		xhash = 47
		xhash ^= hash(self.Item)
		xhash ^= hash(self.Quantity)
		return xhash

def replace_quantity(po_or_items, quantity):
	for item in getattr(po_or_items, 'Items', po_or_items):
		item.Quantity = quantity

def create_purchase_order(items=None, quantity=None, cls=PurchaseOrder):
	items = list() if items is None else items
	items = [items] if not isinstance(items, collections.Sequence) else items
	if quantity is not None:
		quantity = int(quantity)
		replace_quantity(items, quantity)
	result = cls(Items=items, Quantity=quantity)
	return result
