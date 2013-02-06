# -*- coding: utf-8 -*-

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
			external['ChargeID'] = ps.charge_id
			external['TokenID'] = ps.token_id
	
def PurchaseAttemptDecoratorFactory(*args):
	return PurchaseAttemptDecorator()
