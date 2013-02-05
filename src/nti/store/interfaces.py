#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import schema
from zope import interface
from zope import component
from zope.schema.interfaces import IContextSourceBinder
from zope.componentvocabulary.vocabulary import UtilityVocabulary

from nti.utils.property import alias

PA_STATE_UNKNOWN = u'Unknown'
PA_STATE_FAILED = u'Failed'
PA_STATE_PENDING = u'Pending'
PA_STATE_STARTED = u'Started'
PA_STATE_DISPUTED = 'Disputed'
PA_STATE_REFUNDED = u'Refunded'
PA_STATE_CANCELED = u'Canceled'
PA_STATE_RESERVED = u'Reserved'
PA_STATE_SUCCESSFUL = u'Successful'

PA_STATES = (PA_STATE_UNKNOWN, PA_STATE_FAILED, PA_STATE_PENDING, PA_STATE_STARTED, PA_STATE_DISPUTED,
			 PA_STATE_REFUNDED, PA_STATE_SUCCESSFUL, PA_STATE_CANCELED, PA_STATE_RESERVED)
PA_STATE_VOCABULARY = schema.vocabulary.SimpleVocabulary([schema.vocabulary.SimpleTerm( _x ) for _x in PA_STATES] )

class IPaymentProcessor(interface.Interface):
	
	name = schema.TextLine(title='Processor name', required=True)
	
	def process_purchase(user, purchase, amount, currency, description):
		"""
		Process a purchase attempt
		
		:user Entity making the purchase
		:purchase IPurchaseAttempt object
		:amount: purchase amount
		:current: currency ISO code
		:description: purchase description
		"""
	
	def sync_purchase(purchase, user=None):
		"""
		Synchronized the purchase data with the payment processor info
		
		:purchase IPurchaseAttempt object
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
	
	State = schema.Choice(vocabulary=PA_STATE_VOCABULARY, title='purchase state', required=True)
	
	Items = schema.FrozenSet(value_type=schema.TextLine(title='the item identifier'), title="Items being purchased")
	Description = schema.TextLine(title='A purchase description', required=False)
	
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
	
	
class IPurchaseAttemptSynced(component.interfaces.IObjectEvent):
	purchase = interface.Attribute("Purchase attempt")
	
class IPurchaseAttemptEvent(IPurchaseAttemptSynced):
	user = interface.Attribute("The entity that is attempting a purchase")
	state = interface.Attribute('Purchase state')

class IPurchaseAttemptStarted(IPurchaseAttemptEvent):
	pass

class IPurchaseAttemptSuccessful(IPurchaseAttemptEvent):
	pass
	
class IPurchaseAttemptFailed(IPurchaseAttemptEvent):
	error_code = interface.Attribute('Failure code')
	error_message = interface.Attribute('Failure message')

class IPurchaseAttemptRefunded(IPurchaseAttemptEvent):
	pass

@interface.implementer(IPurchaseAttemptSynced)
class PurchaseAttemptSynced(component.interfaces.ObjectEvent):
	purchase = alias('object')
	
@interface.implementer(IPurchaseAttemptEvent)
class PurchaseAttemptEvent(PurchaseAttemptSynced):

	def __init__( self, purchase, user, state):
		super(PurchaseAttemptEvent,self).__init__( purchase )
		self.user = user
		self.state = state

@interface.implementer(IPurchaseAttemptStarted)
class PurchaseAttemptStarted(PurchaseAttemptEvent):

	def __init__( self, purchase, user):
		super(PurchaseAttemptStarted,self).__init__( purchase, user, PA_STATE_STARTED)
				
@interface.implementer(IPurchaseAttemptSuccessful)
class PurchaseAttemptSuccessful(PurchaseAttemptEvent):

	def __init__( self, purchase, user):
		super(PurchaseAttemptSuccessful,self).__init__( purchase, user, PA_STATE_SUCCESSFUL)

@interface.implementer(IPurchaseAttemptSuccessful)
class PurchaseAttemptRefunded(PurchaseAttemptEvent):

	def __init__( self, purchase, user):
		super(PurchaseAttemptRefunded,self).__init__( purchase, user, PA_STATE_REFUNDED)
		
@interface.implementer(IPurchaseAttemptFailed)
class PurchaseAttemptFailed(PurchaseAttemptEvent):

	def __init__( self, purchase, user, error_message=None, error_code=None):
		super(PurchaseAttemptFailed,self).__init__( purchase, user, PA_STATE_FAILED)
		self.error_code = error_code
		self.error_message = error_message
				
class IPurchaseHistory(interface.Interface):
		
	def add_purchase(purchase):
		pass
		
	def remove_purchase(purchase):
		pass
		
	def get_purchase(pid):
		pass
		
	def get_purchase_state(pid):
		pass
	
class ICustomer(interface.Interface):
	pass
