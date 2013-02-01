from __future__ import unicode_literals, print_function, absolute_import

import time

from zope import schema
from zope import interface
from zope import component

from nti.dataserver import interfaces as nti_interfaces

class IItemPurchased(component.interfaces.IObjectEvent):
	user = schema.Object(nti_interfaces.IUser, title="The entity that made the purchase")
	ntiid = schema.TextLine(title="Item purchased identifier")
	time = schema.Float(title="Purchase timestamp")
	transaction_id = schema.TextLine(title="A transaction identifier")

@interface.implementer(IItemPurchased)
class ItemPurchased(component.interfaces.ObjectEvent):

	def __init__( self, user, ntiid, trxid, time=time.time()):
		super(ItemPurchased,self).__init__( user )
		self.time = time
		self.ntiid = ntiid
		self.transaction_id = trxid
	
class IPaymentProcessor(interface.Interface):
	pass
