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
		ntiid = request.matchdict.get('ntiid', u'')
		amount = request.matchdict.get('amount', None)
		currency = request.matchdict.get('currency', 'USD')
		username = request.matchdict.get('user', None)
		username = username or authenticated_userid( request )
		description = request.matchdict.get('description', None)
		description = description or '%s payment for "%s"' % (username, ntiid)
		
		manager = component.getUtility(pay_interfaces.IPaymentManager, name="stripe")
		cid = manager.process_payment(username, token=token, amount=amount, 
									  currency=currency, ntiid=ntiid, description=description)
		
		return {'TransactionID': cid}
		