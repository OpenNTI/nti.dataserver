# -*- coding: utf-8 -*-
"""
FPS purchase functionalilty.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger( __name__ )

import time
import gevent
from datetime import date

from zope import component
from zope import interface
from zope.event import notify

from nti.dataserver.users import User
from nti.dataserver import interfaces as nti_interfaces

from .fps_io import FPSIO
from .. import purchase_history
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
						if t and self._process_fps_status(t.TransactionStatus, purchase_id, username, t.StatusMessage):
							break
						gevent.sleep(5)
				gevent.spawn(process_pay)
						
			return pay_result.TransactionId
		except Exception, e:
			message = str(e)
			notify(store_interfaces.PurchaseAttemptFailed(purchase_id, username, message))
			
	def _get_transactions(self, start_date, token=None, caller_reference=None, status=None):
		result = []
		for t in self.get_account_activity(start_date):
			if	(token is None or t.SenderTokenId == token) and \
				(caller_reference is None or t.CallerReference == caller_reference) and \
				(status is None or t.TransactionStatus == status):
				result.append(t)
		return result;
	
	def sync_purchase(self, purchase_id, username):
		user = User.get_user(username)
		purchase = purchase_history.get_purchase_attempt(purchase_id, username)
		if purchase is None:
			message = 'Purchase %r for user %s could not be found in dB' % (purchase_id, username)
			logger.error(message)
			return None

		trax = None
		fp = pay_interfaces.IFPSPurchase(purchase)
		if fp.TransactionID:
			trax = self.get_transaction(fp.TransactionID)
			if trax is None: 
				message = 'Transaction %s for user %s could not be found in AWS' % (fp.TransactionID, user)
				logger.warn(message)
#		else:
#			start_time = time.mktime(date.fromtimestamp(purchase.StartTime).timetuple())
#			charges = self.get_charges(purchase_id=purchase_id, start_time=start_time, api_key=)
#			if charges:
#				charge = charges[0]
#				notify(pay_interfaces.RegisterStripeCharge(purchase_id, username, charge.id))
#			elif sp.token_id:
#				token = self.get_stripe_token(sp.token_id, api_key=api_key)
#				if token is None:
#					# if the token cannot be found it means there was a db error
#					# or the token has been deleted from stripe.
#					message = 'Purchase %s/%r for user %s could not found in Stripe' % (sp.token_id, purchase_id, username)
#					logger.warn(message)
#					notify(store_interfaces.PurchaseAttemptFailed(purchase_id, username, message))
#				elif token.used:
#					if not purchase.has_completed():
#						# token has been used and no charge has been found, means the transaction failed
#						notify(store_interfaces.PurchaseAttemptFailed(purchase_id, username, message))
#				elif not purchase.is_pending(): #no charge and unused token
#					message = 'Please check status of purchase %r for user %s' % (purchase_id, username)
#					logger.warn(message)
#					
#		if charge:
#			if charge.failure_message:
#				if not purchase.has_failed():
#					notify(store_interfaces.PurchaseAttemptFailed(purchase_id, username, charge.failure_message))
#			elif charge.refunded:
#				if not purchase.is_refunded():
#					notify(store_interfaces.PurchaseAttemptRefunded(purchase_id, username))
#			elif charge.paid:
#				if not purchase.has_succeeded():
#					notify(store_interfaces.PurchaseAttemptSuccessful(purchase_id, username))
#				
#			notify(store_interfaces.PurchaseAttemptSynced(purchase_id, username))
#				
#		return charge
#	
#		class IFPSPurchase(interface.Interface):
#	TokenID = schema.TextLine(title='Token id', required=False)
#	TransactionID = schema.TextLine(title='Transaction id', required=False)
#	CallerReference = schema.TextLine(title='NTIID reference id', required=False)
