# -*- coding: utf-8 -*-
"""
Payments externalization

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import component

from .. import interfaces as store_interfaces
from . import interfaces as payment_interfaces

@component.adapter(store_interfaces.IPurchaseAttempt)
class PurchaseAttemptDecorator(object):
	def decorateExternalObject(self, original, external):
		if original.Processor == 'stripe':
			ps = payment_interfaces.IStripePurchase(original)
			external['TokenID'] = ps.token_id
			external['ChargeID'] = ps.charge_id
		elif original.Processor == 'fps':
			ps = payment_interfaces.IFPSPurchase(original)
			external['TokenID'] = ps.TokenID
			external['TransactionID'] = ps.TransactionID
			external['CallerReference'] = ps.CallerReference
	
def PurchaseAttemptDecoratorFactory(*args):
	return PurchaseAttemptDecorator()
