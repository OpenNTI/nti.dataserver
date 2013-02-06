# -*- coding: utf-8 -*-

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
		
def _StripeCustomerFactory(user):
	result = an_factory(_StripeCustomer)(user)
	return result

@component.adapter(store_interfaces.IPurchaseAttempt)
@interface.implementer( pay_interfaces.IStripePurchase)
class _StripePurchase(zcontained.Contained, Persistent):
	
	TokenID = None
	ChargeID = None
	
	@property
	def purchase(self):
		return self.__parent__
	
	token_id = alias('TokenID')
	charge_id = alias('ChargeID')
	
def _StripePurchaseFactory(purchase):
	result = an_factory(_StripePurchase)(purchase)
	return result
			