# -*- coding: utf-8 -*-
"""
FPS purchase functionalilty.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import time
from datetime import date
from dateutil import parser as date_parser

from zope import interface
from zope.event import notify

from nti.dataserver.users import User

from . import fps_io
from .. import _BasePaymentProcessor
from . import interfaces as fps_interfaces

from ... import payment_charge
from ... import purchase_history
from ... import interfaces as store_interfaces

def _create_payment_charge(trax):
	ta = trax.TransactionAmount
	amount = float(ta.Value)
	currency = trax.CurrencyCode
	name = trax.RecipientName
	created = date_parser.parse(trax.DateCompleted)
	created = time.mktime(created.timetuple())
	result = payment_charge.PaymentCharge(Amount=amount, Currency=currency, Created=created, Name=name)
	return result

@interface.implementer(fps_interfaces.IFPSPaymentProcessor)
class _FPSPaymentProcessor(_BasePaymentProcessor, fps_io.FPSIO):

	name = 'fps'

	def _process_fps_transaction(self, purchase, trax):
		result = True
		status = trax.TransactionStatus
		error_message = trax.StatusMessage
		if status in (store_interfaces.PA_STATE_FAILED, store_interfaces.PA_STATE_FAILURE):
			notify(store_interfaces.PurchaseAttemptFailed(purchase, error_message))
		elif status == store_interfaces.PA_STATE_RESERVED:
			notify(store_interfaces.PurchaseAttemptReserved(purchase))
		elif status == store_interfaces.PA_STATE_SUCCESS:
			pc = _create_payment_charge(trax)
			notify(store_interfaces.PurchaseAttemptSuccessful(purchase, pc))
		else:
			result = False
		return result

	def process_purchase(self, purchase_id, username, token_id, caller_reference, amount, currency='USD'):
		pass
#
# 		purchase = purchase_history.get_purchase_attempt(purchase_id, username)
#
# 		notify(store_interfaces.PurchaseAttemptStarted(purchase))
# 		notify(fps_interfaces.RegisterFPSToken(purchase, token_id, caller_reference))
#
# 		try:
# 			pay_result = self.pay(token=token_id, amount=amount, currency=currency, reference=caller_reference)
# 			notify(fps_interfaces.RegisterFPSTransaction(purchase, pay_result.TransactionId))
#
# 			if not self._process_fps_status(pay_result.TransactionStatus, purchase_id, username):
# 				transaction_id = pay_result.TransactionId
# 				def process_pay():
# 					now = time.time()
# 					while (time.time() - now < 90):
# 						t = self.get_transaction(transaction_id)
# 						if t and self._process_fps_status(purchase, t):
# 							break
# 						gevent.sleep(5)
# 				gevent.spawn(process_pay)
#
# 			return pay_result.TransactionId
# 		except Exception as e:
# 			message = str(e)
# 			notify(store_interfaces.PurchaseAttemptFailed(purchase, message))

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
			logger.error('Purchase %r for user %s could not be found in dB' , purchase_id, username)
			return None

		trax = None
		fp = fps_interfaces.IFPSPurchase(purchase)
		if fp.TransactionID:
			trax = self.get_transaction(fp.TransactionID)
			if trax is None:
				logger.warn('Transaction %s for user %s could not be found in AWS', fp.TransactionID, user)
		else:
			traxs = None
			start_time = time.mktime(date.fromtimestamp(purchase.StartTime).timetuple())
			if fp.TokenID:
				traxs = self._get_transactions(start_time, token=fp.TokenID)
			elif fp.CallerReference:
				traxs = self._get_transactions(start_time, caller_reference=fp.CallerReference)

			trax = traxs[0] if traxs else None

		if trax:
			status = trax.TransactionStatus,
			if	status in (store_interfaces.PA_STATE_FAILED, store_interfaces.PA_STATE_FAILURE) and not purchase.has_failed():
				notify(store_interfaces.PurchaseAttemptFailed(purchase, trax.StatusMessage))
			elif status == store_interfaces.PA_STATE_SUCCESS and not purchase.has_succeeded():
				pc = _create_payment_charge(trax)
				notify(store_interfaces.PurchaseAttemptSuccessful(purchase, pc))
			elif status == store_interfaces.PA_STATE_CANCELED and not purchase.has_failed():
				notify(store_interfaces.PurchaseAttemptFailed(purchase, trax.StatusMessage))
			elif status == store_interfaces.PA_STATE_REFUNDED and not purchase.is_refunded():
				notify(store_interfaces.PurchaseAttemptRefunded(purchase))
			elif status == store_interfaces.PA_STATE_DISPUTED and not purchase.is_disputed():
				notify(store_interfaces.PurchaseAttemptDisputed(purchase))

			notify(store_interfaces.PurchaseAttemptSynced(purchase))

		return trax
