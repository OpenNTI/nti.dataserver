from __future__ import print_function, unicode_literals

from zope import component

from . import interfaces as payment_interfaces

@component.adapter(payment_interfaces.IStripePurchase)
class StripePurchaseDecoratory(object):
	def decorateExternalObject(self, original, external):
		pass
	
def StripePurchaseDecoratorFactory(*args):
	return StripePurchaseDecoratory()
