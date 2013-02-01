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
	pass
