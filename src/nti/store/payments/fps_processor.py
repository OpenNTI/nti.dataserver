# -*- coding: utf-8 -*-
"""
FPS purchase functionalilty.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import time
import gevent

from zope import component
from zope import interface
from zope.event import notify

from nti.dataserver import interfaces as nti_interfaces

from .fps_io import FPSIO
from .. import purchase_history
from .fps_io import FPSException
from . import interfaces as pay_interfaces
from .. import interfaces as store_interfaces
	
@component.adapter(pay_interfaces.IRegisterFPSToken)
def register_fps_token(event):
	def func():
		purchase = purchase_history.get_purchase_attempt(event.purchase_id, event.username)
		fpsp = pay_interfaces.IFPSPurchase(purchase)
		fpsp.token_id = event.token_id
		fpsp.caller_reference = event.caller_reference
	component.getUtility(nti_interfaces.IDataserverTransactionRunner)(func)
	
@component.adapter(pay_interfaces.IRegisterFPSTransaction)
def register_fps_transaction(event):
	def func():
		purchase = purchase_history.get_purchase_attempt(event.purchase_id, event.username)
		fpsp = pay_interfaces.IFPSPurchase(purchase)
		fpsp.transaction_id = event.transaction_id
	component.getUtility(nti_interfaces.IDataserverTransactionRunner)(func)
	
@interface.implementer(pay_interfaces.IFPSPaymentProcessor)
class _FPSPaymentProcessor(FPSIO):
	
	name = 'fps'
	
	def _process_fps_status(self, status, purchase_id, username, error_message=None):
		result = True
		if status in (store_interfaces.PA_STATE_FAILED, store_interfaces.PA_STATE_FAILURE):
			notify(store_interfaces.PurchaseAttemptFailed(purchase_id, username, error_message))
		elif status == store_interfaces.PA_STATE_RESERVED:
			notify(store_interfaces.PurchaseAttemptReserved(purchase_id, username))
		elif status == store_interfaces.PA_STATE_SUCCESS:
			notify(store_interfaces.PurchaseAttemptSuccessful(purchase_id, username))
		else:
			result = False
		return result
			
	def process_purchase(self, purchase_id, username, token_id, caller_reference, amount, currency='USD'):
	
		notify(store_interfaces.PurchaseAttemptStarted(purchase_id, username))
		notify(pay_interfaces.RegisterFPSToken(purchase_id, username, token_id, caller_reference))
		
		try:
			pay_result = self.pay(token=token_id, amount=amount, currency=currency, reference=caller_reference)
			notify(pay_interfaces.RegisterFPSTransaction(purchase_id, username, pay_result.TransactionId))
				
			if not self._process_fps_status(pay_result.TransactionStatus, purchase_id, username):
				transaction_id = pay_result.TransactionId
				def process_pay():
					now = time.time()
					while (time.time() -  now  < 90):
						t = self.get_transaction(transaction_id)
						if self._process_fps_status(t.TransactionStatus, purchase_id, username, t.StatusMessage):
							break
						gevent.sleep(5)
				gevent.spawn(process_pay)
						
			return pay_result.TransactionId
		except FPSException, e:
			message = e.error_message
			notify(store_interfaces.PurchaseAttemptFailed(purchase_id, username, message))
		except Exception, e:
			message = str(e)
			notify(store_interfaces.PurchaseAttemptFailed(purchase_id, username, message))
			
