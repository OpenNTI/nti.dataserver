#!/usr/bin/env python
# -*- coding: utf-8 -*-

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

class IRegisterStripeToken(interface.Interface):
	token = interface.Attribute("The token identifier")
	username = interface.Attribute("The registering username")
	purchase_id = interface.Attribute("The purchase identifier")

@interface.implementer(IRegisterStripeToken)
class RegisterStripeToken(object):
	def __init__( self, purchase_id, token, username=None):
		self.token = token
		self.username = username
		self.purchase_id = purchase_id
	
	token_id = alias('token')
	
class IRegisterStripeCharge(interface.Interface):
	charge_id = interface.Attribute("The charge identifier")
	username = interface.Attribute("The registering username")
	purchase_id = interface.Attribute("The purchase identifier")

@interface.implementer(IRegisterStripeCharge)
class RegisterStripeCharge(object):
	def __init__( self, purchase_id, charge_id, username=None):
		self.username = username
		self.charge_id = charge_id
		self.purchase_id = purchase_id
		
# stripe objects
	
class IStripeCustomer(interface.Interface):
	customer_id = schema.TextLine(title='customer id')
	
class IStripePaymentProcessor(store_interfaces.IPaymentProcessor):
	
	def process_purchase(username, token, purchase_id, amount, currency, description):
		"""
		Process a purchase attempt
		
		:token Credit Card token
		"""

class IStripePurchase(interface.Interface):
	ChargeID = schema.TextLine(title='Charge id', required=False)
	TokenID = schema.TextLine(title='Token id', required=False)
	
