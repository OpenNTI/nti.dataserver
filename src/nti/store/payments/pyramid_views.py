# -*- coding: utf-8 -*-
"""
Payment pyramid views.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger( __name__ )

import gevent

from zope import component

from pyramid.security import authenticated_userid

from .. import purchase_attempt
from .. import purchase_history
from .. import interfaces as store_interfaces

class StripePayment(object):

	processor = 'stripe'
	
	def __init__(self, request):
		self.request = request

	def __call__( self ):
		request = self.request
		items = request.matchdict.get('items', None)
		items = items or request.matchdict.get('nttid', None)
		username = request.matchdict.get('user', None)
		username = username or authenticated_userid( request )
		
		# check for any pending purchase for the items being bought
		purchase = purchase_history.get_pending_purchase_for(username, items)
		if purchase is not None:
			logger.warn("There is already a pending purchase for item(s) %s" % items)
			return purchase
			
				
		token = request.matchdict.get('token')
		amount = request.matchdict.get('amount', None)
		coupon = request.matchdict.get('coupon', None)
		currency = request.matchdict.get('currency', 'USD')
		description = request.matchdict.get('description', None)
		on_behalf_of = request.matchdict.get('on_behalf_of', None)
		description = description or "%s's payment for '%r'" % (username, items)
	
		purchase = purchase_attempt.create_purchase_attempt(items=items, processor=self.processor,
															description=description, on_behalf_of=on_behalf_of)
		purchase_id = purchase_history.register_purchase_attempt(username, purchase)
		
		def process_pay():
			amount = int(amount * 100.0) # cents
			manager = component.getUtility(store_interfaces.IPaymentProcessor, name=self.processor)
			manager.process_purchase(purchase_id=purchase_id, username=username, token=token, amount=amount, 
									 currency=currency, coupon=coupon)
		
		gevent.spawn(process_pay)
		return purchase
		

		