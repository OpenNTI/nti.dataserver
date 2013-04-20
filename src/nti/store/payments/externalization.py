# -*- coding: utf-8 -*-
"""
Payments externalization

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import component
from zope import interface

from nti.externalization import interfaces as ext_interfaces
from nti.externalization.datastructures import InterfaceObjectIO

from . import interfaces as pay_interfaces
from .. import interfaces as store_interfaces
from .fps import interfaces as fps_interfaces
from .stripe import interfaces as stripe_interfaces

@component.adapter(store_interfaces.IPurchaseAttempt)
class PurchaseAttemptDecorator(object):

	def decorateExternalObject(self, original, external):
		if original.Processor == 'stripe':
			ps = stripe_interfaces.IStripePurchase(original)
			external['TokenID'] = ps.token_id
			external['ChargeID'] = ps.charge_id
		elif original.Processor == 'fps':
			ps = fps_interfaces.IFPSPurchase(original)
			external['TokenID'] = ps.TokenID
			external['TransactionID'] = ps.TransactionID
			external['CallerReference'] = ps.CallerReference

def PurchaseAttemptDecoratorFactory(*args):
	return PurchaseAttemptDecorator()

@interface.implementer(ext_interfaces.IInternalObjectIO)
@component.adapter(pay_interfaces.IPayment)
class PaymentExternal(InterfaceObjectIO):
	_ext_iface_upper_bound = pay_interfaces.IPayment
	_excluded_out_ivars_ = InterfaceObjectIO._excluded_out_ivars_ | {'ExpectedAmount', 'ExpectedCurrency'}

