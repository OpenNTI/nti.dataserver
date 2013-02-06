# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import gevent

from zope import component

from pyramid.security import authenticated_userid

from .. import purchase 
from .. import purchase_history
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
		purchase = purchase.create_purchase_attempt(username, items, processor, description=description)
		purchase_id = purchase_history.register_purchase_attempt(username, purchase)
		
		def process_pay():
			manager = component.getUtility(store_interfaces.IPaymentProcessor, name=processor)
			manager.process_purchase(username=username, token=token, amount=amount, 
									 currency=currency, purchase_id=purchase_id, description=description)
		
		gevent.spawn(process_pay)
		return purchase
		
class GetPurchaseAttempt(object):

	def __init__(self, request):
		self.request = request

	def __call__( self ):
		request = self.request
		purchase_id = request.matchdict.get('purchase_id') or request.matchdict.get('OID')
		username = request.matchdict.get('user', None) or authenticated_userid( request )
		purchase = purchase_history.get_purchase_attempt(purchase_id, username)
		if purchase is None:
			request.response.status_int = 404
		return purchase
		