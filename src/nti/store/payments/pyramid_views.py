from __future__ import print_function, unicode_literals, absolute_import

__docformat__ = "restructuredtext en"

import six

from zope import component

from pyramid.security import authenticated_userid

from .. import purchase 
from .. import interfaces as store_interfaces

class StripePayment(object):

	def __init__(self, request):
		self.request = request

	def __call__( self ):
		request = self.request
		token = request.matchdict.get('token')
		items = request.matchdict.get('items', None)
		items = items or request.matchdict.get('nttid', None)
		
		amount = request.matchdict.get('amount', None)
		currency = request.matchdict.get('currency', 'USD')
		username = request.matchdict.get('user', None)
		username = username or authenticated_userid( request )
		description = request.matchdict.get('description', None)
		description = description or '%s payment for "%r"' % (username, items)
		
		processor = 'stripe'
		pa = purchase.create_purchase_attempt_and_start(username, items, processor)
		
		manager = component.getUtility(store_interfaces.IPaymentProcessor, name=processor)
		cid = manager.process_purchase(	user=username, token=token, amount=amount, 
										currency=currency, purchase=pa, description=description)
		
		return {'TransactionID': cid}
		
		
def create_purchase_attempt(items, processor):
	if items is not None:
		items = frozenset([items]) if isinstance(items, six.string_types) else frozenset(items)			
	return purchase.create_purchase_attempt(items, processor)

