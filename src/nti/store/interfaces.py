#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
Store interfaces

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

from zope import interface
from zope.interface.common import sequence
from zope.location.interfaces import IContained
from zope.interface.interfaces import ObjectEvent, IObjectEvent

from dolmen.builtins import IIterable

from nti.contentfragments.schema import HTMLContentFragment

from nti.utils import schema
from zope.schema import vocabulary

# : A :class:`zope.schema.interfaces.IVocabularyTokenized` vocabulary
# : will be available as a registered vocabulary under this name
PURCHASABLE_VOCAB_NAME = 'nti.store.purchasable.vocabulary'

PA_STATE_FAILED = u'Failed'
PA_STATE_SUCCESS = u'Success'
PA_STATE_FAILURE = u'Failure'
PA_STATE_PENDING = u'Pending'
PA_STATE_STARTED = u'Started'
PA_STATE_UNKNOWN = u'Unknown'
PA_STATE_DISPUTED = u'Disputed'
PA_STATE_REFUNDED = u'Refunded'
PA_STATE_CANCELED = u'Canceled'
PA_STATE_RESERVED = u'Reserved'

PA_STATES = (PA_STATE_UNKNOWN, PA_STATE_FAILED, PA_STATE_FAILURE, PA_STATE_PENDING,
			 PA_STATE_STARTED, PA_STATE_DISPUTED, PA_STATE_REFUNDED, PA_STATE_SUCCESS,
			 PA_STATE_CANCELED, PA_STATE_RESERVED)
PA_STATE_VOCABULARY = \
	vocabulary.SimpleVocabulary([vocabulary.SimpleTerm(_x) for _x in PA_STATES])

PAYMENT_PROCESSORS = ('stripe',)
PAYMENT_PROCESSORS_VOCABULARY = \
	vocabulary.SimpleVocabulary([vocabulary.SimpleTerm(_x) for _x in PAYMENT_PROCESSORS])

class IPurchasableStore(interface.Interface):

	def get_purchasable(pid):
		"""
		Return purchasable with the specified id
		"""

	def get_all_purchasables():
		"""
		Return an iterable with purchasable items
		"""

	def get_purchasable_ids():
		"""
		Return an iterable with purchasable ids
		"""

	def __len__():
		"""
		Return the number of items in this store
		"""

class IContentBundle(interface.Interface):
	NTIID = schema.ValidTextLine(title='Content bundle NTTID', required=True)
	Title = schema.ValidTextLine(title='Content bundle title', required=False)
	Author = schema.ValidTextLine(title='Content bundle author', required=False)
	Description = HTMLContentFragment(title='Content bundle description', required=False, default='')
	Items = schema.FrozenSet(value_type=schema.ValidTextLine(title='The item identifier'),
							 title="Bundle items")

class IPurchasable(IContentBundle):
	Amount = schema.Float(title="Cost amount", required=True, min=0.0)
	Currency = schema.ValidTextLine(title='Currency amount', required=True, default='USD')
	Discountable = schema.Bool(title="Discountable flag", required=True, default=False)
	BulkPurchase = schema.Bool(title="Bulk purchase flag", required=True, default=False)
	Fee = schema.Float(title="Percentage fee", required=False, min=0.0)
	Icon = schema.ValidTextLine(title='Icon URL', required=False)
	Thumbnail = schema.ValidTextLine(title='Thumbnail URL', required=False)
	Provider = schema.ValidTextLine(title='Purchasable item provider', required=True)
	License = schema.ValidTextLine(title='Purchasable license', required=False)

class ICourse(IPurchasable):
	Name = schema.ValidTextLine(title='Course Name', required=False)
	Featured = schema.Bool(title='Featured flag', required=False, default=False)
	Preview = schema.Bool(title='Course preview flag', required=False)
	StartDate = schema.ValidTextLine(title="Course start date", required=False)
	Department = schema.ValidTextLine(title='Course Department', required=False)
	Signature = schema.ValidText(title='Course/Professor Signature', required=False)
	Communities = schema.FrozenSet(value_type=schema.ValidTextLine(title='The community identifier'),
								   title="Communities")
	# overrides
	Amount = schema.Float(title="Cost amount", required=False, min=0.0)
	Currency = schema.ValidTextLine(title='Currency amount', required=False)
	Provider = schema.ValidTextLine(title='Course provider', required=False)

	# Temporary BWC to match CourseCatalogEntry
	Duration = schema.Timedelta(title="The length of the course",
								description="Currently optional, may be None",
								required=False)
	EndDate = schema.Datetime( title="The date on which the course ends",
							   description="Currently optional; a missing value means the course has no defined end date.",
							   required=False)


class IPriceable(interface.Interface):
	NTIID = schema.ValidTextLine(title='Purchasable item NTTID', required=True)
	Quantity = schema.Int(title="Quantity", required=False, default=1, min=0)

	def copy():
		"""makes a new copy of this priceable"""

class IPurchaseItem(IPriceable):
	"""marker interface for a purchase order item"""

class IPurchaseOrder(sequence.IMinimalSequence):
	Items = schema.Tuple(value_type=schema.Object(IPriceable), title='The items',
						 required=True, min_length=1)
	Quantity = schema.Int(title='Purchase bulk quantity (overwrites-item quantity)',
						  required=False)

	def copy():
		"""makes a new copy of this purchase order"""

class IPricedItem(IPriceable):
	PurchaseFee = schema.Float(title="Fee Amount", required=False)
	PurchasePrice = schema.Float(title="Cost amount", required=True)
	NonDiscountedPrice = schema.Float(title="Non discounted price", required=False)
	Currency = schema.ValidTextLine(title='Currency ISO code', required=True, default='USD')

class IPricingResults(interface.Interface):
	Items = schema.List(value_type=schema.Object(IPricedItem), title='The priced items',
						required=True, min_length=0)
	TotalPurchaseFee = schema.Float(title="Fee Amount", required=False)
	TotalPurchasePrice = schema.Float(title="Cost amount", required=True)
	TotalNonDiscountedPrice = schema.Float(title="Non discounted price", required=False)
	Currency = schema.ValidTextLine(title='Currency ISO code', required=True, default='USD')

class IUserAddress(interface.Interface):
	Street = schema.ValidText(title='Street address', required=False)
	City = schema.ValidTextLine(title='The city name', required=False)
	State = schema.ValidTextLine(title='The state', required=False)
	Zip = schema.ValidTextLine(title='The zip code', required=False, default=u'')
	Country = schema.ValidTextLine(title='The country', required=False, default='USA')

class IPaymentCharge(interface.Interface):
	Amount = schema.Float(title="Change amount", required=True)
	Created = schema.Float(title="Created timestamp", required=True)
	Currency = schema.ValidTextLine(title='Currency amount', required=True, default='USD')
	CardLast4 = schema.Int(title='CreditCard last 4 digits', required=False)
	Name = schema.ValidTextLine(title='The customer/charge name', required=False)
	Address = schema.Object(IUserAddress, title='User address', required=False)

class IPurchaseError(interface.Interface):
	Type = schema.ValidTextLine(title='Error type', required=True)
	Code = schema.ValidTextLine(title='Error code', required=False)
	Message = schema.ValidText(title='Error message', required=True)

class INTIStoreException(interface.Interface):
	""" marker interface for store exceptions """

class IPurchasablePricer(interface.Interface):

	def price(priceable):
		"""
		price the specfied priceable
		"""

	def evaluate(priceables):
		"""
		price the specfied priceables
		"""

class IPaymentProcessor(interface.Interface):

	name = schema.ValidTextLine(title='Processor name', required=True)

	def validate_coupon(coupon):
		"""
		validate the specified coupon
		"""

	def apply_coupon(amount, coupon):
		"""
		apply the specified coupon to the specified amout
		"""

	def process_purchase(purchase_id, username, expected_amount=None):
		"""
		Process a purchase attempt

		:purchase_id purchase identifier
		:username User making the purchase
		:expected_amount: expected amount
		"""

	def refund_purchase(purchase_id):
		"""
		Refund a purchase attempt

		:purchase_id purchase identifier
		:username User making the purchase
		:expected_amount: expected amount
		"""

	def sync_purchase(purchase_id, username):
		"""
		Synchronized the purchase data with the payment processor info

		:purchase purchase identifier
		:user User that made the purchase
		"""

class IPurchaseAttempt(IContained):

	Processor = schema.Choice(vocabulary=PAYMENT_PROCESSORS_VOCABULARY,
							  title='purchase processor', required=True)

	State = schema.Choice(vocabulary=PA_STATE_VOCABULARY, title='Purchase state',
						  required=True)

	Order = schema.Object(IPurchaseOrder, title="Purchase order", required=True)
	Description = schema.ValidTextLine(title='A purchase description', required=False)

	StartTime = schema.Number(title='Start time', required=True)
	EndTime = schema.Number(title='Completion time', required=False)

	Pricing = schema.Object(IPricingResults, title='Pricing results', required=False)
	Error = schema.Object(IPurchaseError, title='Error object', required=False)
	Synced = schema.Bool(title='if the item has been synchronized with the processors data',
						 required=True, default=False)

	def has_completed():
		"""
		return if the purchase has completed
		"""

	def has_failed():
		"""
		return if the purchase has failed
		"""

	def has_succeeded():
		"""
		return if the purchase has been successful
		"""

	def is_unknown():
		"""
		return if state of the purchase is unknown
		"""

	def is_pending():
		"""
		return if the purchase is pending (started)
		"""

	def is_refunded():
		"""
		return if the purchase has been refunded
		"""

	def is_disputed():
		"""
		return if the purchase has been disputed
		"""

	def is_reserved():
		"""
		return if the purchase has been reserved with the processor
		"""

	def is_canceled():
		"""
		return if the purchase has been canceled
		"""

	def is_synced():
		"""
		return if the purchase has been synchronized with the payment processor
		"""

class IInvitationPurchaseAttempt(IPurchaseAttempt):
	pass

class IEnrollmentAttempt(IPurchaseAttempt):
	pass

class IRedeemedPurchaseAttempt(IPurchaseAttempt):
	RedemptionTime = schema.Number(title='Redemption time', required=True)
	RedemptionCode = schema.ValidTextLine(title='Redemption Code', required=True)

class IEnrollmentPurchaseAttempt(IEnrollmentAttempt):
	Processor = schema.ValidTextLine(title='Enrollment institution', required=False)

class IPurchaseAttemptEvent(IObjectEvent):
	object = schema.Object(IPurchaseAttempt, title="The purchase")

class IPurchaseAttemptSynced(IPurchaseAttemptEvent):
	pass

class IPurchaseAttemptVoided(IPurchaseAttemptEvent):
	pass

class IPurchaseAttemptStateEvent(IPurchaseAttemptEvent):
	state = interface.Attribute('Purchase state')

class IPurchaseAttemptStarted(IPurchaseAttemptStateEvent):
	pass

class IPurchaseAttemptSuccessful(IPurchaseAttemptStateEvent):
	charge = interface.Attribute('Purchase charge')
	request = interface.Attribute('Purchase pyramid request')

class IPurchaseAttemptRefunded(IPurchaseAttemptStateEvent):
	pass

class IPurchaseAttemptDisputed(IPurchaseAttemptStateEvent):
	pass

class IPurchaseAttemptReserved(IPurchaseAttemptStateEvent):
	pass

class IPurchaseAttemptFailed(IPurchaseAttemptStateEvent):
	error = interface.Attribute('Failure error')


class IEnrollmentAttemptEvent(IPurchaseAttemptEvent):
	object = schema.Object(IEnrollmentAttempt, title="The enrollment")

class IEnrollmentAttemptSuccessful(IEnrollmentAttemptEvent):
	request = interface.Attribute('Pyramid request')

class IUnenrollmentAttemptSuccessful(IEnrollmentAttemptEvent):
	request = interface.Attribute('Pyramid request')

@interface.implementer(IPurchaseAttemptEvent)
class PurchaseAttemptEvent(ObjectEvent):

	@property
	def purchase(self):
		return self.object

@interface.implementer(IPurchaseAttemptSynced)
class PurchaseAttemptSynced(PurchaseAttemptEvent):
	pass

@interface.implementer(IPurchaseAttemptVoided)
class PurchaseAttemptVoided(PurchaseAttemptEvent):
	pass

@interface.implementer(IPurchaseAttemptStarted)
class PurchaseAttemptStarted(PurchaseAttemptEvent):
	state = PA_STATE_STARTED

@interface.implementer(IPurchaseAttemptSuccessful)
class PurchaseAttemptSuccessful(PurchaseAttemptEvent):
	state = PA_STATE_SUCCESS
	def __init__(self, purchase, charge=None, request=None):
		super(PurchaseAttemptSuccessful, self).__init__(purchase)
		self.charge = charge
		self.request = request

@interface.implementer(IPurchaseAttemptRefunded)
class PurchaseAttemptRefunded(PurchaseAttemptEvent):
	state = PA_STATE_REFUNDED

@interface.implementer(IPurchaseAttemptDisputed)
class PurchaseAttemptDisputed(PurchaseAttemptEvent):
	state = PA_STATE_DISPUTED

@interface.implementer(IPurchaseAttemptReserved)
class PurchaseAttemptReserved(PurchaseAttemptEvent):
	state = PA_STATE_RESERVED

@interface.implementer(IPurchaseAttemptFailed)
class PurchaseAttemptFailed(PurchaseAttemptEvent):

	error = None
	state = PA_STATE_FAILED

	def __init__(self, purchase, error=None):
		super(PurchaseAttemptFailed, self).__init__(purchase)
		self.error = error

@interface.implementer(IEnrollmentAttemptEvent)
class EnrollmentAttemptEvent(PurchaseAttemptEvent):
	pass

@interface.implementer(IEnrollmentAttemptSuccessful)
class EnrollmentAttemptSuccessful(EnrollmentAttemptEvent):

	def __init__(self, purchase, request=None):
		super(EnrollmentAttemptSuccessful, self).__init__(purchase)
		self.request = request

@interface.implementer(IUnenrollmentAttemptSuccessful)
class UnenrollmentAttemptSuccessful(EnrollmentAttemptEvent):

	def __init__(self, purchase, request=None):
		super(UnenrollmentAttemptSuccessful, self).__init__(purchase)
		self.request = request

class IPurchaseHistory(IIterable):

	def add_purchase(purchase):
		pass

	def remove_purchase(purchase):
		pass

	def get_purchase(pid):
		pass

	def get_purchase_state(pid):
		pass

	def get_purchase_history(start_time=None, end_time=None):
		pass

	def values():
		"""
		Return all purchase attempts
		"""
class IStorePurchaseInvitation(interface.Interface):
	pass
