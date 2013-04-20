# -*- coding: utf-8 -*-
"""
Payment interfaces

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import schema
from zope import interface

from nti.utils import schema as nti_schema

from .. import interfaces as store_interfaces

class ICouponPriceable(store_interfaces.IPriceable):
	Coupon = nti_schema.ValidTextLine(title="The coupon", required=False)

class IRegisterPurchaseData(interface.Interface):
	object = schema.Object(store_interfaces.IPurchaseAttempt, title="The purchase", required=True)

class RegisterPurchaseData(object):

	def __init__(self, obj):
		self.object = obj

	@property
	def purchase(self):
		return self.object
