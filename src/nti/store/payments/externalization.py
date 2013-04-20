# -*- coding: utf-8 -*-
"""
Payments externalization

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import component

from .. import interfaces as store_interfaces
from .fps import interfaces as fps_interfaces
from .stripe import interfaces as stripe_interfaces

@component.adapter(store_interfaces.IPurchaseAttempt)
class PurchaseAttemptDecorator(object):

	def decorateExternalObject(self, original, external):
		if original.Processor == 'stripe':
			ps = stripe_interfaces.IStripePurchaseAttempt(original)
			external['TokenID'] = ps.token_id
			external['ChargeID'] = ps.charge_id
		elif original.Processor == 'fps':
			ps = fps_interfaces.IFPSPurchase(original)
			external['TokenID'] = ps.TokenID
			external['TransactionID'] = ps.TransactionID
			external['CallerReference'] = ps.CallerReference

def PurchaseAttemptDecoratorFactory(*args):
	return PurchaseAttemptDecorator()
