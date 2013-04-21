# -*- coding: utf-8 -*-
"""
Stripe purchase adapters.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import BTrees

from zope import component
from zope import interface
from zope.annotation import factory as an_factory
from zope.container import contained as zcontained

from persistent import Persistent

from nti.dataserver import interfaces as nti_interfaces

from nti.utils.property import alias

from .utils import makenone
from . import StripePurchaseError
from . import interfaces as stripe_interfaces
from ... import interfaces as store_interfaces

@component.adapter(nti_interfaces.IUser)
@interface.implementer(stripe_interfaces.IStripeCustomer)
class _StripeCustomer(zcontained.Contained, Persistent):

	family = BTrees.family64

	CustomerID = None

	def __init__(self):
		self.Charges = self.family.OO.OOTreeSet()

	@property
	def id(self):
		return self.CustomerID

	def __contains__(self, charge):
		return  charge in self.Charges

	charges = alias('Charges')
	customer_id = alias('CustomerID')

_StripeCustomerFactory = an_factory(_StripeCustomer)

@component.adapter(store_interfaces.IPurchaseAttempt)
@interface.implementer(stripe_interfaces.IStripePurchaseAttempt)
class _StripePurchaseAttempt(zcontained.Contained, Persistent):

	TokenID = None
	ChargeID = None

	@property
	def purchase(self):
		return self.__parent__

	token_id = alias('TokenID')
	charge_id = alias('ChargeID')

_StripePurchaseAttemptFactory = an_factory(_StripePurchaseAttempt)

@component.adapter(basestring)
@interface.implementer(stripe_interfaces.IStripePurchaseError)
def _string_purchase_error(message):
	result = StripePurchaseError(Type=u"Error")
	result.Message = unicode(message or u'')
	return result

@component.adapter(stripe_interfaces.IStripeException)
@interface.implementer(stripe_interfaces.IStripePurchaseError)
def stripe_exception_adpater(error):
	result = StripePurchaseError(Type=u"Exception")
	args = getattr(error, 'args', ())
	message = unicode(' '.join(map(str, args)))
	result.Message = message or 'Unspecified Stripe Exception'
	return result

@component.adapter(stripe_interfaces.IStripeError)
@interface.implementer(stripe_interfaces.IStripePurchaseError)
def stripe_error_adpater(error):
	result = StripePurchaseError(Type=u"Error")
	result.HttpStatus = getattr(error, 'http_status', None)
	args = getattr(error, 'args', ())
	message = makenone(error.message) or ' '.join(map(str, args))
	result.Message = unicode(message or 'Unspecified Stripe Error')
	return result

@component.adapter(stripe_interfaces.IStripeAPIError)
@interface.implementer(stripe_interfaces.IStripePurchaseError)
def stripe_api_error_adpater(error):
	result = stripe_error_adpater(error)
	result.Type = u"APIError"
	return result

@component.adapter(stripe_interfaces.IStripeAPIConnectionError)
@interface.implementer(stripe_interfaces.IStripePurchaseError)
def stripe_api_connection_error_adpater(error):
	result = stripe_error_adpater(error)
	result.Type = "APIConnectionError"
	return result

@component.adapter(stripe_interfaces.IStripeCardError)
@interface.implementer(stripe_interfaces.IStripePurchaseError)
def stripe_card_error_adpater(error):
	result = stripe_error_adpater(error)
	result.Type = u"CardError"
	result.Code = makenone(getattr(error, 'code', None))
	result.Param = makenone(getattr(error, 'param', None))
	return result

@component.adapter(stripe_interfaces.IStripeCardError)
@interface.implementer(stripe_interfaces.IStripeInvalidRequestError)
def stripe_invalid_request_error_adpater(error):
	result = stripe_error_adpater(error)
	result.Type = u"InvalidRequestError"
	return result

@component.adapter(stripe_interfaces.IStripeAuthenticationError)
@interface.implementer(stripe_interfaces.IStripePurchaseError)
def stripe_auth_error_adpater(error):
	result = stripe_error_adpater(error)
	result.Type = u"AuthenticationError"
	return result
