# -*- coding: utf-8 -*-
"""
Stripe Payment interfaces

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import schema
from zope import interface

from nti.utils.property import alias as _alias

from .. import interfaces as pay_interfaces
from ... import interfaces as store_interfaces

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

class IRegisterStripeToken(pay_interfaces.IRegisterPurchaseData):
	token = interface.Attribute("The token identifier")

@interface.implementer(IRegisterStripeToken)
class RegisterStripeToken(pay_interfaces.RegisterPurchaseData):

	def __init__( self, purchase_id, username, token_id):
		super(RegisterStripeToken, self).__init__(purchase_id, username)
		self.token_id = token_id

	token = _alias('token_id')

class IRegisterStripeCharge(pay_interfaces.IRegisterPurchaseData):
	charge_id = interface.Attribute("The charge identifier")

@interface.implementer(IRegisterStripeCharge)
class RegisterStripeCharge(pay_interfaces.RegisterPurchaseData):

	def __init__( self, purchase_id, username, charge_id):
		super(RegisterStripeCharge, self).__init__(purchase_id, username)
		self.charge_id = charge_id

# stripe objects

class IStripeCustomer(interface.Interface):
	CustomerID = schema.TextLine(title='customer id')
	Charges = schema.Set(value_type=schema.TextLine(title='the charge id'), title='customer stripe charges')

class IStripePaymentProcessor(store_interfaces.IPaymentProcessor):

	def validate_coupon(coupon):
		"""
		validate the specfied coupon
		"""

	def apply_coupon(amount, coupon=None):
		"""
		apply the specfied coupon to the specfied amount
		"""

	def process_purchase(purchase_id, username, token, amount, currency, coupon):
		"""
		Process a purchase attempt

		:token Credit Card token
		"""

class IStripePurchase(interface.Interface):
	ChargeID = schema.TextLine(title='Charge id', required=False)
	TokenID = schema.TextLine(title='Token id', required=False)

class IStripeAccessKey(interface.Interface):
	alias = interface.Attribute( "Key name or alias" )
	value = interface.Attribute( "The actual key value")
