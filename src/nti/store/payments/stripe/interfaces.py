# -*- coding: utf-8 -*-
"""
Stripe Payment interfaces

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import schema
from zope import interface

from nti.dataserver import interfaces as nti_interfaces

from nti.utils import schema as nti_schema
from nti.utils.property import alias as _alias

from .. import interfaces as pay_interfaces
from ... import interfaces as store_interfaces

class IStripePayment(pay_interfaces.IPayment):
	Coupon = nti_schema.ValidTextLine(title="The stripe coupon", required=False)

class IStripeCustomerCreated(interface.Interface):
	user = schema.Object(nti_interfaces.IUser, title="The user")
	customer_id = nti_schema.ValidTextLine(title="The stripe customer identifier")

@interface.implementer(IStripeCustomerCreated)
class StripeCustomerCreated(object):

	def __init__(self, user, customer_id):
		self.user = user
		self.customer_id = customer_id

class IStripeCustomerDeleted(IStripeCustomerCreated):
	pass

@interface.implementer(IStripeCustomerDeleted)
class StripeCustomerDeleted(StripeCustomerCreated):
	pass

class IRegisterStripeToken(pay_interfaces.IRegisterPurchaseData):
	token = nti_schema.ValidTextLine(title="The token identifier")

@interface.implementer(IRegisterStripeToken)
class RegisterStripeToken(pay_interfaces.RegisterPurchaseData):

	def __init__(self, purchase, token_id):
		super(RegisterStripeToken, self).__init__(purchase)
		self.token_id = token_id

	token = _alias('token_id')

class IRegisterStripeCharge(pay_interfaces.IRegisterPurchaseData):
	charge_id = nti_schema.ValidTextLine(title="The charge identifier")

@interface.implementer(IRegisterStripeCharge)
class RegisterStripeCharge(pay_interfaces.RegisterPurchaseData):

	def __init__(self, purchase, charge_id):
		super(RegisterStripeCharge, self).__init__(purchase)
		self.charge_id = charge_id

# stripe objects

class IStripeCustomer(interface.Interface):
	CustomerID = nti_schema.ValidTextLine(title='customer id')
	Charges = schema.Set(value_type=nti_schema.ValidTextLine(title='the charge id'), title='customer stripe charges')

class IStripePaymentProcessor(store_interfaces.IPaymentProcessor):

	def create_token(customer_id=None, number=None, exp_month=None, exp_year=None, cvc=None, api_key=None, **kwargs):
		"""
		Create a stripe token
		
		:customer_id Stripe customer id
		:number Credit card number
		:exp_month Expiration month
		:exp_year Expiration year
		:cvc CVC number
		"""

	def validate_coupon(coupon):
		"""
		validate the specfied coupon
		"""

	def apply_coupon(amount, coupon=None):
		"""
		apply the specfied coupon to the specfied amount
		"""

	def process_purchase(purchase_id, username, token, amount, currency, coupon):
		"""
		Process a purchase attempt

		:token Credit Card token
		"""

class IStripeCoupon(interface.Interface):
	"""marker interface for a stripe coupon"""

class IStripePriceable(store_interfaces.IPriceable):
	Coupon = schema.Object(interface.Interface, title='the coupon', required=False)

class IStripePricedPurchasable(store_interfaces.IPricedPurchasable):
	Coupon = schema.Object(IStripeCoupon, title='the coupon', required=False)

class IStripePurchase(interface.Interface):
	ChargeID = nti_schema.ValidTextLine(title='Charge id', required=False)
	TokenID = nti_schema.ValidTextLine(title='Token id', required=False)

class IStripeConnectKey(interface.Interface):
	Alias = nti_schema.ValidTextLine(title='Key name or alias', required=True)
	PrivateKey = nti_schema.ValidTextLine(title="The private key", required=True)
	LiveMode = schema.Bool(title="Live mode flag", required=False)
	StripeUserID = nti_schema.ValidTextLine(title="String user id", required=False)
	RefreshToken = nti_schema.ValidTextLine(title="Refresh token", required=False)
	PublicKey = nti_schema.ValidTextLine(title="The private key", required=False)

class IStripePurchaseError(store_interfaces.IPurchaseError):
	HttpStatus = schema.Int(title='HTTP Status', required=False)
	Param = nti_schema.ValidTextLine(title="Optional parameter", required=False)

# stripe interfaces

class IStripeException(interface.Interface):
	"""marker interface for a stripe exception"""

class IStripeError(interface.Interface):
	"""marker interface for a stripe errors"""

class IStripeAPIError(IStripeError):
	"""marker interface for a stripe api error"""

class IStripeAPIConnectionError(IStripeError):
	"""marker interface for a stripe api connection error"""

class IStripeCardError(IStripeError):
	"""marker interface for a stripe card errors"""

class IStripeInvalidRequestError(IStripeError):
	"""marker interface for a stripe invalid request errors"""

class IStripeAuthenticationError(IStripeError):
	"""marker interface for a stripe authentication errors"""
