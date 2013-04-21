# -*- coding: utf-8 -*-
"""
FPS Payment interfaces

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import schema
from zope import interface

from .. import interfaces as pay_interfaces
from ... import interfaces as store_interfaces

class IFPSPurchaseAttempt(interface.Interface):
	TokenID = schema.TextLine(title='Token id', required=False)
	TransactionID = schema.TextLine(title='Transaction id', required=False)
	CallerReference = schema.TextLine(title='NTIID reference id', required=False)

class IRegisterFPSToken(pay_interfaces.IRegisterPurchaseData):
	token_id = interface.Attribute("The token identifier")
	caller_reference = interface.Attribute("The nttid caller identifier")

class IRegisterFPSTransaction(pay_interfaces.IRegisterPurchaseData):
	transaction_id = interface.Attribute("The purchase identifier")

@interface.implementer(IRegisterFPSToken)
class RegisterFPSToken(pay_interfaces.RegisterPurchaseData):
	def __init__(self, purchase, token_id, caller_reference):
		super(RegisterFPSToken, self).__init__(purchase)
		self.token_id = token_id
		self.caller_reference = caller_reference

@interface.implementer(IRegisterFPSTransaction)
class RegisterFPSTransaction(pay_interfaces.RegisterPurchaseData):
	def __init__(self, purchase, transaction_id):
		super(RegisterFPSTransaction, self).__init__(purchase)
		self.transaction_id = transaction_id

class IFPSPaymentProcessor(store_interfaces.IPaymentProcessor):

	def process_purchase(purchase_id, username, token_id, caller_reference, amount, currency, description):
		"""
		Process a purchase attempt

		:token Credit Card token
		"""

class IFPSAccessKey(interface.Interface):
	alias = interface.Attribute( "Key name or alias" )
	value = interface.Attribute( "The actual key value")
