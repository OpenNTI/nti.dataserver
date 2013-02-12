# -*- coding: utf-8 -*-
"""
Payment interfaces

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import schema
from zope import interface

from nti.utils.property import alias

from .. import interfaces as store_interfaces
		
# stripe events
		
class IStripeCustomerCreated(interface.Interface):
	username = interface.Attribute("The entity that was created")
	customer_id = interface.Attribute("The stripe customer identifier")

@interface.implementer(IStripeCustomerCreated)
class StripeCustomerCreated(object):
	def __init__( self, username, customer_id):
		self.username = username
		self.customer_id = customer_id
	
class IStripeCustomerDeleted(IStripeCustomerCreated):
	pass

@interface.implementer(IStripeCustomerDeleted)
class StripeCustomerDeleted(StripeCustomerCreated):
	pass

class IRegisterPurchaseData(interface.Interface):
	username = interface.Attribute("The registering username")
	purchase_id = interface.Attribute("The purchase identifier")
	
class RegisterPurchaseData(object):
	def __init__( self, purchase_id, username):
		self.username = username
		self.purchase_id = purchase_id
	
class IRegisterStripeToken(IRegisterPurchaseData):
	token = interface.Attribute("The token identifier")
	
@interface.implementer(IRegisterStripeToken)
class RegisterStripeToken(RegisterPurchaseData):
	def __init__( self, purchase_id, username, token_id):
		super(RegisterStripeToken, self).__init__(purchase_id, username)
		self.token_id = token_id

	token = alias('token_id')
	
class IRegisterStripeCharge(IRegisterPurchaseData):
	charge_id = interface.Attribute("The charge identifier")

@interface.implementer(IRegisterStripeCharge)
class RegisterStripeCharge(RegisterPurchaseData):
	def __init__( self, purchase_id, username, charge_id):
		super(RegisterStripeCharge, self).__init__(purchase_id, username)
		self.charge_id = charge_id
		
# stripe objects
	
class IStripeCustomer(interface.Interface):
	CustomerID = schema.TextLine(title='customer id')
	
class IStripePaymentProcessor(store_interfaces.IPaymentProcessor):
	
	def process_purchase(purchase_id, username, token_id, amount, currency, description):
		"""
		Process a purchase attempt
		
		:token Credit Card token
		"""

class IStripePurchase(interface.Interface):
	ChargeID = schema.TextLine(title='Charge id', required=False)
	TokenID = schema.TextLine(title='Token id', required=False)
	
class IFPSPurchase(interface.Interface):
	TokenID = schema.TextLine(title='Token id', required=False)
	TransactionID = schema.TextLine(title='Transaction id', required=False)
	CallerReference = schema.TextLine(title='NTIID reference id', required=False)
	
class IRegisterFPSToken(IRegisterPurchaseData):
	token_id = interface.Attribute("The token identifier")
	caller_reference = interface.Attribute("The nttid caller identifier")

class IRegisterFPSTransaction(IRegisterPurchaseData):
	transaction_id = interface.Attribute("The purchase identifier")

@interface.implementer(IRegisterFPSToken)
class RegisterFPSToken(RegisterPurchaseData):
	def __init__( self, purchase_id, username, token_id, caller_reference):
		super(RegisterFPSToken, self).__init__(purchase_id, username)
		self.token_id = token_id
		self.caller_reference = caller_reference

@interface.implementer(IRegisterFPSTransaction)
class RegisterFPSTransaction(RegisterPurchaseData):
	def __init__( self, purchase_id, username, transaction_id):
		super(RegisterFPSTransaction, self).__init__(purchase_id, username)
		self.transaction_id = transaction_id
		
class IFPSPaymentProcessor(store_interfaces.IPaymentProcessor):
	
	def process_purchase(purchase_id, username, token_id, caller_reference, amount, currency, description):
		"""
		Process a purchase attempt
		
		:token Credit Card token
		"""
		
	