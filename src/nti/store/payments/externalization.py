from __future__ import print_function, unicode_literals

from zope import component

from . import interfaces as payment_interfaces

@component.adapter(payment_interfaces.IStripePurchase)
class StripePurchaseDecorator(object):
	def decorateExternalObject(self, original, external):
		ps = component.getAdapter(original, payment_interfaces.IStripePurchase)
		external['ChargeID'] = ps.charge_id
		external['TokenID'] = ps.token_id
	
def StripePurchaseDecoratorFactory(*args):
	return StripePurchaseDecorator()
