from __future__ import unicode_literals, print_function, absolute_import

from zope import schema
from zope import interface
from zope import component

from nti.utils.property import alias

STRIPE_PROCESSOR = 'stripe'
AMAZON_PROCESSOR = 'amazon'

PA_STATE_UNKNOWN = 'Unknown'
PA_STATE_FAILED = 'Failed'
PA_STATE_PENDING = 'Pending'
PA_STATE_STARTED = 'Started'
PA_STATE_SUCCESSFUL = 'Successful'
		
class IPurchaseAttempt(interface.Interface):
	
	Processor = schema.Choice(values=(STRIPE_PROCESSOR,AMAZON_PROCESSOR),
							  title='purchase processor', required=True)
	
	State = schema.Choice(values=(PA_STATE_UNKNOWN, PA_STATE_FAILED, PA_STATE_PENDING, PA_STATE_STARTED, PA_STATE_SUCCESSFUL),
						  title='purchase state', required=True)
	
	Items = schema.FrozenSet(value_type=schema.TextLine(title='the item identifier'), title="Items being purchased")
	
	StartTime = schema.Float(title='Start time', required=True)
	EndTime = schema.Float(title='Completion time', required=False)
	
	ErrorCode = schema.Int(title='Failure code', required=False)
	ErrorMessage = schema.TextLine(title='Failure message', required=False)
	
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
	
class IPurchaseAttemptEvent(component.interfaces.IObjectEvent):
	purchase = interface.Attribute("Purchase attempt")
	user = interface.Attribute("The entity that is attempting a purchase")
	state = interface.Attribute('Purchase state')

class IPurchaseAttemptStarted(IPurchaseAttemptEvent):
	pass

class IPurchaseAttemptSuccessful(IPurchaseAttemptEvent):
	pass
	
class IPurchaseAttemptFailed(IPurchaseAttemptEvent):
	error_code = interface.Attribute('Failure code')
	error_message = interface.Attribute('Failure message')

@interface.implementer(IPurchaseAttemptEvent)
class PurchaseAttemptEvent(component.interfaces.ObjectEvent):

	def __init__( self, purchase, user, state):
		super(PurchaseAttemptEvent,self).__init__( purchase )
		self.user = user
		self.state = state
	
	purchase = alias('object')
	
@interface.implementer(IPurchaseAttemptStarted)
class PurchaseAttemptStarted(PurchaseAttemptEvent):

	def __init__( self, purchase, user):
		super(PurchaseAttemptStarted,self).__init__( purchase, user, PA_STATE_STARTED)
				
@interface.implementer(IPurchaseAttemptSuccessful)
class PurchaseAttemptSuccessful(PurchaseAttemptEvent):

	def __init__( self, purchase, user):
		super(PurchaseAttemptSuccessful,self).__init__( purchase, user, PA_STATE_SUCCESSFUL)

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
