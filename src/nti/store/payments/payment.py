# -*- coding: utf-8 -*-
"""
Defines payment.

$Id: purchasable.py 18394 2013-04-18 19:27:11Z carlos.sanchez $
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import collections

from zope import interface
from zope.mimetype import interfaces as zmime_interfaces
from zope.schema.fieldproperty import FieldPropertyStoredThroughField as FP

from nti.utils.schema import SchemaConfigured

from ..utils import MetaStoreObject
from . import interfaces as pay_interfaces

@interface.implementer(pay_interfaces.IPayment, zmime_interfaces.IContentTypeAware)
class Payment(SchemaConfigured):

	__metaclass__ = MetaStoreObject

	Items = FP(pay_interfaces.IPayment['Items'])
	Description = FP(pay_interfaces.IPayment['Description'])
	ExpectedAmount = FP(pay_interfaces.IPayment['ExpectedAmount'])
	ExpectedCurrency = FP(pay_interfaces.IPayment['ExpectedCurrency'])

	def __getitem__(self, index):
		return self.Items[index]

	def __iter__(self):
		return iter(self.Items)

	def __str__(self):
		return self.Description

	def __repr__(self):
		return "%s(%s,%s,%s,%s)" % (self.__class__.__name__, self.Description, self.Items,
									self.ExpectedAmount, self.ExpectedCurrency)

	def __eq__(self, other):
		try:
			return self is other or (self.Items == other.Items)
		except AttributeError:
			return NotImplemented

	def __hash__(self):
		xhash = 47
		xhash ^= hash(self.Items)
		return xhash

def create_payment(items, description, amount=None, currency='USD'):
	items = [items] if not isinstance(items, collections.Sequence) else items
	amount = float(amount) if amount is not None else None
	result = Payment(Items=items, Description=description, ExpectedAmount=amount, ExpectedCurrency=currency)
	return result
