#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import time

from zope import schema
from zope import interface

from .. import interfaces as store_interfaces
	
class IItemsPurchased(interface.Interface):
	items = interface.Attribute("Iterable of items purchased")
	time = schema.Float(title="event timestamp", required=False)
	purchase_id = schema.TextLine(title="The purchase identifier")
	user = interface.Attribute("The entity that made the purchase")

class IItemsReturned(IItemsPurchased):
	pass

@interface.implementer(IItemsPurchased)
class ItemsPurchased(object):

	def __init__( self, user, items, purchase_id, time=time.time()):
		self.time = time
		self.user = user
		self.items = items
		self.purchase_id = purchase_id
	
@interface.implementer(IItemsReturned)
class ItemsReturned(ItemsPurchased):
	pass
		
class IStripeCustomer(interface.Interface):
	customer_id = schema.TextLine(title='customer id')
	
class IStripePaymentProcessor(store_interfaces.IPaymentProcessor):
	
	def process_purchase(user, token, purchase, amount, currency, description):
		"""
		Process a purchase attempt
		
		:token Credit Card token
		"""

class IStripePurchase(interface.Interface):
	ChargeID = schema.TextLine(title='Charge id', required=False)
	TokenID = schema.TextLine(title='Token id', required=False)
	
