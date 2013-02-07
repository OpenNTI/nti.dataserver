# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import hmac
import uuid
import base64
import hashlib

from boto.fps.connection import FPSConnection

class FPSException(Exception):
	pass

class FPSIO(object):
	
	def __init__(self, host='fps.sandbox.amazonaws.com'):
		self._connection = None
		
	@property
	def connection(self):
		if self._connection is None:
			self._connection = FPSConnection(host=self.aws_host)
		return self._connection
	
	def _get_token_by_caller(self, reference=None, token=None):
		"""
		return meta informacion for the specied token
		
		token: senderTokenID return by AWS-fps after a payment operation (cbi)
		reference: buyer/caller/NTI transaction reference id
		"""
		assert reference or token
		
		fps = self.connection
		if token:
			result = fps.get_token_by_caller(TokenId=token)
		elif reference:
			result = fps.get_token_by_caller(CallerReference=reference)
		else:
			result = None
		return result

	def _get_cbui_url(self, amount, reference, returnURL, currency='USD', paymentReason=None, pipelineName='SingleUse'):
		"""
		return an [aws-fps] url to start a payment process
		
		amount : transaction amount
		reference: buyer/caller/NTI transaction reference id
		returnURL: URL to return to after payment operation (submit/cancalation)
		pipelineName: Type of payment (see FPSConnection#cbui_url)
		"""
		paymentReason = paymentReason or ''
		inputs = {
				'transactionAmount':	amount,
				'currencyCode':		 	currency,
				'pipelineName':			pipelineName,
				'returnURL':			returnURL,
				'paymentReason':		paymentReason,
				'CallerReference':		reference,
				'signature':			self.signature()
		}
		url = self.connection.cbui_url(**inputs)
		return url

	def signature(self, msg=None):
		msg = msg or str(uuid.uuid1())
		dig = hmac.new(self.aws_secret_access_key, msg=msg, digestmod=hashlib.sha256).digest()
		return base64.b64encode(dig).decode() 
	
	def get_account_activity(self, startDate=None):
		response = self.connection.get_account_activity(StartDate=startDate)
		return response
	
	def get_account_balance(self):
		response = self.connection.get_account_balance()
		return response
	
	def pay(self, token, amount, currency='USD', reference=None):
		inputs = {
			'TransactionAmount.Value':			amount,
			'TransactionAmount.CurrencyCode':	currency,
			'SenderTokenId':					token,
			'CallerReference':					reference,
		}
		result = self.connection.pay(**inputs)
		return result
	
	def get_transaction(self, transaction_id):
		result = self.connection.get_transaction(TransactionId=transaction_id)
		return result
