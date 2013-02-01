from __future__ import print_function, unicode_literals, absolute_import

__docformat__ = "restructuredtext en"

from zope import component

from pyramid.security import authenticated_userid

from . import interfaces as pay_interfaces

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
		
		manager = component.getUtility(pay_interfaces.IPaymentProcessor, name="stripe")
		cid = manager.process_payment(username, token=token, amount=amount, 
									  currency=currency, items=items, description=description)
		
		return {'TransactionID': cid}
		