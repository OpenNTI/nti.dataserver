from __future__ import unicode_literals, print_function, absolute_import

import time

from zope import schema
from zope import interface
from zope import component

from nti.dataserver import interfaces as nti_interfaces

class IItemPurchased(component.interfaces.IObjectEvent):
	user = schema.Object(nti_interfaces.IUser, title="The entity that made the purchase")
	ntiid = schema.TextLine(title="Item purchsed identifier")
	time = schema.Float(title="Purchase timestamp")
	transactionid = schema.TextLine(title="A transaction identifier")

@interface.implementer(IItemPurchased)
class ItemPurchased(component.interfaces.ObjectEvent):

	def __init__( self, user, ntiid, trxid, time=time.time()):
		super(ItemPurchased,self).__init__( user )
		self.time = time
		self.ntiid = ntiid
		self.transactionid = trxid


class IStripeCustomer(interface.Interface):
	customer_id = schema.Text(title='Custome id', required=True)
	card = schema.Text(title='Token for last card use', required=False)
	charges = schema.Dict(title='Customer purchase charges',
							key_type=schema.TextLine(title='charge id'),
							value_type=schema.TextLine(title='item purchased id (i.e. NTIID)'))
	
	

class IPaymentManager(interface.Interface):
	pass