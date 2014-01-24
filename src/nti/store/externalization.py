#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
Store externalization

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface
from zope import component

from nti.externalization import interfaces as ext_interfaces
from nti.externalization.datastructures import InterfaceObjectIO

from . import interfaces as store_interfaces

@interface.implementer(ext_interfaces.IInternalObjectIO)
@component.adapter(store_interfaces.IPurchaseItem)
class PurchaseItemExternal(InterfaceObjectIO):
	_ext_iface_upper_bound = store_interfaces.IPurchaseItem

@interface.implementer(ext_interfaces.IInternalObjectIO)
@component.adapter(store_interfaces.IPurchaseOrder)
class PurchaseOrderExternal(InterfaceObjectIO):
	_ext_iface_upper_bound = store_interfaces.IPurchaseOrder

@interface.implementer(ext_interfaces.IInternalObjectIO)
@component.adapter(store_interfaces.IPurchaseError)
class PurchaseErrorExternal(InterfaceObjectIO):
	_ext_iface_upper_bound = store_interfaces.IPurchaseError

@interface.implementer(ext_interfaces.IInternalObjectIO)
@component.adapter(store_interfaces.IPurchaseAttempt)
class PurchaseAttemptExternal(InterfaceObjectIO):
	_ext_iface_upper_bound = store_interfaces.IPurchaseAttempt

@interface.implementer(ext_interfaces.IInternalObjectIO)
@component.adapter(store_interfaces.IInvitationPurchaseAttempt)
class InvitationPurchaseAttemptExternal(InterfaceObjectIO):
	_ext_iface_upper_bound = store_interfaces.IInvitationPurchaseAttempt

@interface.implementer(ext_interfaces.IInternalObjectIO)
@component.adapter(store_interfaces.IRedeemedPurchaseAttempt)
class RedeemedPurchaseAttemptExternal(InterfaceObjectIO):
	_ext_iface_upper_bound = store_interfaces.IRedeemedPurchaseAttempt

@interface.implementer(ext_interfaces.IInternalObjectIO)
@component.adapter(store_interfaces.IPurchasable)
class PurchasableExternal(InterfaceObjectIO):
	_ext_iface_upper_bound = store_interfaces.IPurchasable

@interface.implementer(ext_interfaces.IInternalObjectIO)
@component.adapter(store_interfaces.IPriceable)
class PriceableExternal(InterfaceObjectIO):
	_ext_iface_upper_bound = store_interfaces.IPriceable

@interface.implementer(ext_interfaces.IInternalObjectIO)
@component.adapter(store_interfaces.IPricedItem)
class PricedItemExternal(InterfaceObjectIO):
	_ext_iface_upper_bound = store_interfaces.IPricedItem
	_excluded_out_ivars_ = InterfaceObjectIO._excluded_out_ivars_ | {'PurchaseFee'}

@interface.implementer(ext_interfaces.IInternalObjectIO)
@component.adapter(store_interfaces.IPricingResults)
class PricingResultsExternal(InterfaceObjectIO):
	_ext_iface_upper_bound = store_interfaces.IPricingResults
	_excluded_out_ivars_ = InterfaceObjectIO._excluded_out_ivars_ | {'TotalPurchaseFee'}
