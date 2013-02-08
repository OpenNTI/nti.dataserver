# -*- coding: utf-8 -*-
"""
AWS FPS adapters

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import interface
from zope import component
from zope.annotation import factory as an_factory
from zope.container import contained as zcontained

from persistent import Persistent

from nti.utils.property import alias

from . import interfaces as pay_interfaces
from .. import interfaces as store_interfaces

@component.adapter(store_interfaces.IPurchaseAttempt)
@interface.implementer(pay_interfaces.IFPSPurchase)
class _FPSPurchase(zcontained.Contained, Persistent):
	
	TokenID = None
	TransactionID = None
	
	@property
	def purchase(self):
		return self.__parent__
	
	token_id = alias('TokenID')
	transaction_id = alias('TransactionID')
	
_FPSPurchaseFactory = an_factory(_FPSPurchase)
