# -*- coding: utf-8 -*-
"""
Stripe purchase adapters.

$Id: stripe_adapters.py 15718 2013-02-08 03:30:41Z carlos.sanchez $
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import interface
from zope import component
from zope.annotation import factory as an_factory
from zope.container import contained as zcontained

from persistent import Persistent

from nti.dataserver import interfaces as nti_interfaces

from nti.utils.property import alias

from . import interfaces as pay_interfaces
from .. import interfaces as store_interfaces

@component.adapter(nti_interfaces.IUser)
@interface.implementer( pay_interfaces.IStripeCustomer)
class _StripeCustomer(Persistent):
	
	customer_id = None
	
	@property
	def id(self):
		return self.customer_id
		
_StripeCustomerFactory = an_factory(_StripeCustomer)

@component.adapter(store_interfaces.IPurchaseAttempt)
@interface.implementer(pay_interfaces.IStripePurchase)
class _StripePurchase(zcontained.Contained, Persistent):
	
	TokenID = None
	ChargeID = None
	
	@property
	def purchase(self):
		return self.__parent__
	
	token_id = alias('TokenID')
	charge_id = alias('ChargeID')
	
_StripePurchaseFactory = an_factory(_StripePurchase)
			