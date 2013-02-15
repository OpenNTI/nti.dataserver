# -*- coding: utf-8 -*-
"""
FDP IO operations

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import os
import hmac
import time
import uuid
import base64
import hashlib
import numbers
import urlparse
from datetime import date

from boto.exception import BotoServerError
from boto.fps.connection import FPSConnection
from boto.fps.exception import InvalidTransactionId
from boto.fps.exception import InvalidCallerReference

SINGLE_USE_PIPIELINE = 'SingleUse'
AWS_FPS_SANDBOX_HOST = 'fps.sandbox.amazonaws.com'

class FPSException(Exception):
	pass

class FPSIO(object):
	
	def __init__(self):
		self._connection = None
		
	@property
	def connection(self):
		if self._connection is None:
			aws_host = os.getenv('AWS_FPS_HOST', AWS_FPS_SANDBOX_HOST)
			self._connection = FPSConnection(host=aws_host)
		return self._connection
	
	def signature(self, msg=None):
		msg = msg or str(uuid.uuid1())
		secret_access_key = self.connection.provider.secret_key
		dig = hmac.new(secret_access_key, msg=msg, digestmod=hashlib.sha256).digest()
		return base64.b64encode(dig).decode() 
	
	def _do_fps_operation(self,func, *args, **kwargs):
		try:
			result = func(*args, **kwargs)
			return result
		except BotoServerError, e:
			raise e
		except Exception, e:
			raise FPSException(str(e))
		
	def get_cbui_url(self, return_url, amount, currency='USD',caller_reference=None, payment_reason=None, pipeline_name=None):
		"""
		Returns a [aws-fps] url to start a payment process
		
		:return_url: URL to return to after payment operation (submit/cancalation)
		:caller_reference:  buyer/caller/NTI transaction reference id
		"""
		payment_reason = payment_reason or ''
		pipeline_name = pipeline_name or SINGLE_USE_PIPIELINE
		caller_reference = caller_reference or str(uuid.uuid1())
		inputs = {
				'transactionAmount':	amount,
				'currencyCode':		 	currency,
				'pipelineName':			pipeline_name,
				'returnURL':			return_url,
				'paymentReason':		payment_reason,
				'CallerReference':		caller_reference
		}
		url = self._do_fps_operation(self.connection.cbui_url, **inputs)
		return url

	def get_account_activity(self, start_date=None):
		"""
		Return the transactions starting from the specified date
		"""
		start_date = start_date or time.time()
		if isinstance(start_date, numbers.Real):
			d = date.fromtimestamp(start_date)
			start_date = d.strftime("%Y-%m-%d")
		result = self._do_fps_operation(self.connection.get_account_activity, StartDate=start_date)
		result = result.GetAccountActivityResult.Transaction # this the list of transactions
		return result
	
	def get_transaction(self, transaction_id):
		try:
			result = self._do_fps_operation(self.connection.get_transaction, TransactionId=transaction_id)
			result = result.GetTransactionResult.Transaction
		except InvalidTransactionId:
			result = None
		return result
	
	def get_account_balance(self):
		result = self._do_fps_operation(self.connection.get_account_balance)
		result = result.GetAccountBalanceResult.AccountBalance
		return result
	
	def get_token_by_caller(self, token=None, caller_reference=None):
		try:
			result = self._do_fps_operation(self.connection.get_token_by_caller, TokenId=token, allerReference=caller_reference)
			result = result.GetTokenByCallerResult
		except InvalidCallerReference:
			result = None
		return result
	
	def pay(self, token, amount, currency='USD', reference=None):
		inputs = {
			'TransactionAmount.Value':			amount,
			'TransactionAmount.CurrencyCode':	currency,
			'SenderTokenId':					token,
			'CallerReference':					reference,
		}
		result = self.connection.pay(**inputs)
		return result
	
	def parse_aws_response(self, path):
		parsed_path = urlparse.urlparse(path)
		result = { k:v for k,v in urlparse.parse_qsl(parsed_path.query) }
		if 'errorMessage' in result:
			raise FPSException(result['errorMessage'])
		return result
