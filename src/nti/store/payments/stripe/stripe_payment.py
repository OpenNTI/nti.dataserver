# -*- coding: utf-8 -*-
"""
Defines stripe payment object.

$Id: purchasable.py 18394 2013-04-18 19:27:11Z carlos.sanchez $
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import interface
from zope.schema.fieldproperty import FieldPropertyStoredThroughField as FP

from ..payment import Payment
from . import interfaces as stripe_interfaces
from ...utils import MetaStoreObject, to_frozenset

@interface.implementer(stripe_interfaces.IStripePayment)
class StripePayment(Payment):

	__metaclass__ = MetaStoreObject

	Coupon = FP(stripe_interfaces.IStripePayment['Coupon'])

	def __str__(self):
		return "%s,%s" % (self.Items, self.Description)

	def __repr__(self):
		return "%s(%s,%s,%s,%s,%s)" % (self.__class__.__name__, self.Items, self.Description,
									   self.ExpectedAmount, self.ExpectedCurrency, self.Coupon)

	def __eq__(self, other):
		try:
			return self is other or (self.Items == other.Items
									 and self.Coupon == other.Coupon)
		except AttributeError:
			return NotImplemented

	def __hash__(self):
		xhash = 47
		xhash ^= hash(self.Items)
		xhash ^= hash(self.Coupon)
		return xhash

def create_stripe_payment(items, description, coupon=None, amount=None, currency='USD'):
	items = to_frozenset(items)
	currency = currency or 'USD'
	amount = float(amount) if amount is not None else None
	result = StripePayment(Items=items, Description=description, Coupon=coupon,
						   ExpectedAmount=amount, ExpectedCurrency=currency)
	return result
