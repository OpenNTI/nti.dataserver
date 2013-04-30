# -*- coding: utf-8 -*-
"""
Store interfaces

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import schema
from zope import interface
from zope.interface.common import sequence
from zope.location.interfaces import IContained
from zope.interface.interfaces import ObjectEvent, IObjectEvent

from nti.utils import schema as nti_schema
from nti.contentfragments.schema import HTMLContentFragment

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

PA_STATES = (PA_STATE_UNKNOWN, PA_STATE_FAILED, PA_STATE_FAILURE, PA_STATE_PENDING, PA_STATE_STARTED, PA_STATE_DISPUTED,
			 PA_STATE_REFUNDED, PA_STATE_SUCCESS, PA_STATE_CANCELED, PA_STATE_RESERVED)
PA_STATE_VOCABULARY = schema.vocabulary.SimpleVocabulary([schema.vocabulary.SimpleTerm(_x) for _x in PA_STATES])

PAYMENT_PROCESSORS = ('stripe', 'fps')
PAYMENT_PROCESSORS_VOCABULARY = schema.vocabulary.SimpleVocabulary([schema.vocabulary.SimpleTerm(_x) for _x in PAYMENT_PROCESSORS])

class IPurchasable(interface.Interface):
	NTIID = nti_schema.ValidTextLine(title='Purchasable item NTTID', required=True)
	Title = nti_schema.ValidTextLine(title='Purchasable item title', required=False)
	Author = nti_schema.ValidTextLine(title='Purchasable item author', required=False)
	Description = HTMLContentFragment(title='Purchasable item description', required=False, default='')  # TODO: Right interface?
	Amount = schema.Float(title="Cost amount", required=True)
	Currency = nti_schema.ValidTextLine(title='Currency amount', required=True, default='USD')
	Discountable = schema.Bool(title="Discountable flag", required=True, default=False)
	BulkPurchase = schema.Bool(title="Bulk purchase flag", required=True, default=False)
	Fee = schema.Float(title="Percentage fee", required=False)
	Icon = nti_schema.ValidTextLine(title='Icon URL', required=False)
	Provider = nti_schema.ValidTextLine(title='Purchasable item provider', required=True)
	Emails = schema.FrozenSet(value_type=nti_schema.ValidTextLine(title='The email'), title="Purchasable associated emails")
	Items = schema.FrozenSet(value_type=nti_schema.ValidTextLine(title='The item identifier'), title="Purchasable content items")

class IPriceable(interface.Interface):
	NTIID = nti_schema.ValidTextLine(title='Purchasable item NTTID', required=True)
	Quantity = schema.Int(title="Quantity", required=False, default=1)

	def copy():
		"""makes a new copy of this priceable"""

class IPurchaseItem(IPriceable):
	"""marker interface for a purchase order item"""

class IPurchaseOrder(sequence.IMinimalSequence):
	Items = schema.Tuple(value_type=schema.Object(IPriceable), title='The items', required=True, min_length=1)
	Quantity = schema.Int(title='Purchase bulk quantity', required=False)

	def copy():
		"""makes a new copy of this purchase order"""

class IPricedItem(IPriceable):
	PurchaseFee = schema.Float(title="Fee Amount", required=False)
	PurchasePrice = schema.Float(title="Cost amount", required=True)
	NonDiscountedPrice = schema.Float(title="Non discounted price", required=False)
	Currency = nti_schema.ValidTextLine(title='Currency ISO code', required=True, default='USD')

class IPricingResults(interface.Interface):
	Items = schema.List(value_type=schema.Object(IPricedItem), title='The priced items', required=True, min_length=0)
	TotalPurchaseFee = schema.Float(title="Fee Amount", required=False)
	TotalPurchasePrice = schema.Float(title="Cost amount", required=True)
	TotalNonDiscountedPrice = schema.Float(title="Non discounted price", required=False)
	Currency = nti_schema.ValidTextLine(title='Currency ISO code', required=True, default='USD')

class IUserAddress(interface.Interface):
	Street = nti_schema.ValidText(title='Street address', required=False)
	City = nti_schema.ValidTextLine(title='The city name', required=False)
	State = nti_schema.ValidTextLine(title='The state', required=False)
	Zip = nti_schema.ValidTextLine(title='The zip code', required=False, default=u'')
	Country = nti_schema.ValidTextLine(title='The country', required=False, default='USA')

class IPaymentCharge(interface.Interface):
	Amount = schema.Float(title="Change amount", required=True)
	Created = schema.Float(title="Created timestamp", required=True)
	Currency = nti_schema.ValidTextLine(title='Currency amount', required=True, default='USD')
	CardLast4 = schema.Int(title='CreditCard last 4 digists', required=False)
	Name = nti_schema.ValidTextLine(title='The customer/charge name', required=False)
	Address = schema.Object(IUserAddress, title='User address', required=False)

class IPurchaseError(interface.Interface):
	Type = nti_schema.ValidTextLine(title='Error type', required=True)
	Code = nti_schema.ValidTextLine(title='Error code', required=False)
	Message = nti_schema.ValidText(title='Error message', required=True)

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

	name = nti_schema.ValidTextLine(title='Processor name', required=True)

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

	def sync_purchase(purchase_id, username):
		"""
		Synchronized the purchase data with the payment processor info

		:purchase purchase identifier
		:user User that made the purchase
		"""

class IPurchaseAttempt(IContained):

	Processor = schema.Choice(vocabulary=PAYMENT_PROCESSORS_VOCABULARY, title='purchase processor', required=True)

	State = schema.Choice(vocabulary=PA_STATE_VOCABULARY, title='Purchase state', required=True)

	Order = schema.Object(IPurchaseOrder, title="Purchase order", required=True)
	Description = nti_schema.ValidTextLine(title='A purchase description', required=False)

	StartTime = nti_schema.Number(title='Start time', required=True)
	EndTime = nti_schema.Number(title='Completion time', required=False)

	Pricing = schema.Object(IPricingResults, title='Pricing results', required=False)
	Error = schema.Object(IPurchaseError, title='Error object', required=False)
	Synced = schema.Bool(title='if the item has been synchronized with the processors data', required=True, default=False)

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

class IRedeemedPurchaseAttempt(IPurchaseAttempt):
	RedemptionTime = nti_schema.Number(title='Redemption time', required=True)
	RedemptionCode = nti_schema.ValidTextLine(title='Redemption Code', required=True)

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

class IPurchaseHistory(interface.Interface):

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

class IStorePurchaseInvitation(interface.Interface):
	pass
