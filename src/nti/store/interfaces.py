# -*- coding: utf-8 -*-
"""
Store interfaces

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import schema
from zope import interface
from zope.schema.interfaces import IContextSourceBinder
from zope.componentvocabulary.vocabulary import UtilityVocabulary

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
PA_STATE_VOCABULARY = schema.vocabulary.SimpleVocabulary([schema.vocabulary.SimpleTerm( _x ) for _x in PA_STATES] )

class IPaymentProcessor(interface.Interface):

	name = schema.TextLine(title='Processor name', required=True)

	def process_purchase(username, purchase_id, amount, currency, description):
		"""
		Process a purchase attempt

		:username User making the purchase
		:purchase purchase identifier
		:amount: purchase amount
		:current: currency ISO code
		:description: purchase description
		"""

	def sync_purchase(purchase_id, username):
		"""
		Synchronized the purchase data with the payment processor info

		:purchase purchase identifier
		:user User that made the purchase
		"""

class PaymentProcessorVocabulary(UtilityVocabulary):
	nameOnly = False
	interface = IPaymentProcessor

def payment_processors(context):
	return PaymentProcessorVocabulary(context)
interface.directlyProvides(payment_processors, IContextSourceBinder)

class IPurchaseAttempt(interface.Interface):

	Processor = schema.Choice(source=payment_processors, title='purchase processor', required=True)

	State = schema.Choice(vocabulary=PA_STATE_VOCABULARY, title='Purchase state', required=True)

	Items = schema.FrozenSet(value_type=schema.TextLine(title='The item identifier'), title="Items being purchased")
	Description = schema.TextLine(title='A purchase description', required=False)
	OnBehalfOf = schema.FrozenSet(value_type=schema.TextLine(title='username'), title='List of users', required=False, min_length=0)

	StartTime = schema.Float(title='Start time', required=True)
	EndTime = schema.Float(title='Completion time', required=False)

	ErrorCode = schema.Int(title='Failure code', required=False)
	ErrorMessage = schema.TextLine(title='Failure message', required=False)

	Synced = schema.Bool(title='if the item has been synchronized with the processors data', required=True)

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

class IPurchaseAttemptEvent(interface.Interface):
	purchase_id = interface.Attribute("Purchase attempt id")
	username = interface.Attribute("The purchase's entity")

class IPurchaseAttemptSynced(IPurchaseAttemptEvent):
	pass

class IPurchaseAttemptVoided(IPurchaseAttemptEvent):
	pass

class IPurchaseAttemptStateEvent(IPurchaseAttemptEvent):
	state = interface.Attribute('Purchase state')

class IPurchaseAttemptStarted(IPurchaseAttemptStateEvent):
	pass

class IPurchaseAttemptSuccessful(IPurchaseAttemptStateEvent):
	pass

class IPurchaseAttemptRefunded(IPurchaseAttemptStateEvent):
	pass

class IPurchaseAttemptDisputed(IPurchaseAttemptStateEvent):
	pass

class IPurchaseAttemptReserved(IPurchaseAttemptStateEvent):
	pass

class IPurchaseAttemptFailed(IPurchaseAttemptStateEvent):
	error_code = interface.Attribute('Failure code')
	error_message = interface.Attribute('Failure message')

@interface.implementer(IPurchaseAttemptEvent)
class PurchaseAttemptEvent(object):
	def __init__( self, purchase_id, username):
		self.username = username
		self.purchase_id = purchase_id

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

	error_code = None
	state = PA_STATE_FAILED

	def __init__( self, purchase_id, username, error_message=None, error_code=None):
		super(PurchaseAttemptFailed,self).__init__( purchase_id, username)
		self.error_message = error_message
		if error_code:
			self.error_code = error_code

class IPurchaseHistory(interface.Interface):

	def add_purchase(purchase):
		pass

	def remove_purchase(purchase):
		pass

	def get_purchase(pid):
		pass

	def get_purchase_state(pid):
		pass
