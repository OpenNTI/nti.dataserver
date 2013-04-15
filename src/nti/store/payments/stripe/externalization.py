# -*- coding: utf-8 -*-
"""
Stripe externalization

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import six

from zope import interface
from zope import component

from nti.externalization import interfaces as ext_interfaces
from nti.externalization.datastructures import LocatedExternalDict

from nti.externalization.interfaces import IInternalObjectIO
from nti.externalization.datastructures import InterfaceObjectIO

from . import interfaces as stripe_interfaces

@interface.implementer(IInternalObjectIO)
@component.adapter(stripe_interfaces.IStripeConnectKey)
class StripeConnectKeyExternal(InterfaceObjectIO):
	_ext_iface_upper_bound = stripe_interfaces.IStripeConnectKey
	_excluded_out_ivars_ = InterfaceObjectIO._excluded_out_ivars_ | { 'PrivateKey', 'RefreshToken' }


def _makenone(s):
	if isinstance(s, six.string_types) and s == 'None':
		s = None
	return s

@interface.implementer(ext_interfaces.IExternalObject)
@component.adapter(stripe_interfaces.IStripeCoupon)
class StripeCouponExternalizer(object):

	__slots__ = ('coupon',)

	def __init__(self, coupon):
		self.coupon = coupon

	def toExternalObject(self):
		result = LocatedExternalDict()
		result['ID'] = self.coupon.id
		if _makenone(self.coupon.duration):
			result['Duration'] = self.coupon.duration
		if self.coupon.amount_off:
			result['AmountOff'] = self.coupon.amount_off
			result['Currency'] = _makenone(self.coupon.currency) or 'USD'
		if self.coupon.percent_off:
			result['PercentOff'] = self.coupon.percent_off
		if self.coupon.duration_in_months:
			result['DurationInMonths'] = self.coupon.duration_in_months
		if self.coupon.redeem_by:
			result['RedeemBy'] = self.coupon.redeem_by
		if self.coupon.times_redeemed is not None:
			result['TimesRedeemed'] = self.coupon.times_redeemed
		if self.coupon.max_redemptions:
			result['MaxRedemptions'] = self.coupon.max_redemptions
		return result
