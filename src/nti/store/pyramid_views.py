# -*- coding: utf-8 -*-
"""
Store pyramid views.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import time

from zope import component

from pyramid.security import authenticated_userid

from . import purchase_history
from . import interfaces as store_interfaces

class GetPendingPurchases(object):
	
	def __init__(self, request):
		self.request = request

	def __call__( self ):
		request = self.request
		username = request.matchdict.get('user', None)
		username = username or authenticated_userid( request )
		purchases = purchase_history.get_pending_purchases(username)
		return purchases

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
		elif purchase.is_pending():
			start_time = purchase.StartTime
			# more than 90 secs try to sync
			if time.time() - start_time >= 90 and not purchase.is_synced():
				manager = component.getUtility(store_interfaces.IPaymentProcessor, name=purchase.Processor)
				manager.sync_purchase(purchase_id, username)
		return purchase
