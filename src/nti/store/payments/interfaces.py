from __future__ import unicode_literals, print_function, absolute_import

import time

from zope import schema
from zope import interface

class IItemsPurchased(interface.Interface):
	items = interface.Attribute("Iterable of items purchased")
	user = interface.Attribute("The entity that made the purchase")
	time = schema.Float(title="Purchase timestamp")
	purchase_id = schema.TextLine(title="A purchase (trx) identifier")

@interface.implementer(IItemsPurchased)
class ItemsPurchased(object):

	def __init__( self, user, items, purchase_id, time=time.time()):
		self.time = time
		self.user = user
		self.items = items
		self.purchase_id = purchase_id
	
class IStripeCustomer(interface.Interface):
	customer_id = schema.TextLine(title='customer id')
	
class IPaymentProcessor(interface.Interface):
	
	def process_purchase(user, purchase, amount, currency, description):
		"""
		Process a purchase attempt
		
		:user Entity making the purchase
		:purchase IPurchaseAttempt object
		:amount: purchase amount
		:current: currency ISO code
		:description: purchase description
		"""
		
class IStripePaymentProcessor(IPaymentProcessor):
	
	def process_purchase(user, token, purchase, amount, currency, description):
		"""
		Process a purchase attempt
		
		:token Credit Card token
		"""

class IStripePurchase(interface.Interface):
	charge_id = schema.TextLine(title='charge id')
	token_id = schema.TextLine(title='token id')
	
