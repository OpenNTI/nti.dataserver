from __future__ import unicode_literals, print_function, absolute_import

from zope import schema
from zope import interface
from zope import component

from nti.dataserver import interfaces as nti_interfaces

from nti.utils.property import alias

STRIPE_PROCESSOR = 'stripe'
AMAZON_PROCESSOR = 'amazon'

TRX_UNKNOWN = 'Unknown'
TRX_FAILED = 'Failed'
TRX_PENDING = 'Pending'
TRX_STARTED = 'Started'
TRX_SUCCESSFUL = 'Successful'
		
class ITransaction(interface.Interface):
	
	processor = schema.Choice(values=(STRIPE_PROCESSOR,AMAZON_PROCESSOR),
							  title='transaction processor', required=True)
	transaction_id = schema.TextLine(title="A transaction identifier", required=True)
	
	state = schema.Choice(values=(TRX_UNKNOWN, TRX_FAILED, TRX_PENDING, TRX_STARTED, TRX_SUCCESSFUL),
						  title='Transaction state', required=True)
	
	start_time = schema.Float(title='start time')
	end_time = schema.Float(title='Completion time', required=False)
	
	failure_code = schema.Int(title='Failure code', required=False)
	failure_message = schema.TextLine(title='Failure message', required=False)
	
	def hasCompleted():
		"""
		return if the transaction has completed
		"""
	
	def hasFailed():
		"""
		return if the transaction has failed
		"""
		
	def hasSucceeded():
		"""
		return if the transaction has been successful
		"""
		
	def isPending():
		"""
		return if the transaction is pending (started)
		"""
	
class ITransactionEvent(component.interfaces.IObjectEvent):
	user = schema.Object(nti_interfaces.IUser, title="The entity that made the purchase")
	event = schema.Choice(values=(TRX_FAILED, TRX_PENDING, TRX_STARTED, TRX_SUCCESSFUL), title='Transaction state')
	transaction = schema.Object(ITransaction, title="Transaction State")

class ITransactionCompleted(ITransactionEvent):
	transaction_id = schema.TextLine(title="Transaction identifer")
	
class ITransactionFailed(ITransactionEvent):
	pass

@interface.implementer(ITransactionEvent)
class TransactionEvent(component.interfaces.ObjectEvent):

	def __init__( self, user, transaction, event):
		super(TransactionEvent,self).__init__( user )
		self.event = event
		self.transaction = transaction
		
	trx = alias('transaction')
		
	@property
	def transaction_id(self):
		self.transaction.transaction_id
	
@interface.implementer(ITransactionCompleted)
class TransactionCompleted(TransactionEvent):

	def __init__( self, user, transaction, event, transaction_id=None):
		super(TransactionCompleted,self).__init__( user, transaction, event)
		self._transaction_id = transaction_id or transaction.transaction_id
				
	@property
	def transaction_id(self):
		self._transaction_id
	
@interface.implementer(ITransactionFailed)
class TransactionFailed(TransactionEvent):

	def __init__( self, user, transaction, failure_message=None, failure_code=None):
		super(TransactionFailed,self).__init__( user, transaction, TRX_FAILED)
		self.failure_code = failure_code 
		self.failure_message = failure_message
				
CUSTOMER_CREATED = 'Created'
CUSTOMER_DELETED = 'Deleted'
	
class ICustomerEvent(component.interfaces.IObjectEvent):
	user = schema.Object(nti_interfaces.IUser, title="The user")
	type = schema.Choice(values=(CUSTOMER_CREATED, CUSTOMER_DELETED), title='Event type')
	processor =  schema.TextLine(title='Processor', required=False)
	customer_id = schema.TextLine(title='Customer id', required=False)

@interface.implementer(ICustomerEvent)
class CustomerEvent(component.interfaces.ObjectEvent):

	def __init__( self, user, event_type, customer_id=None, processor=None):
		super(CustomerEvent,self).__init__( user )
		self.customer_id = customer_id
		self.processor = processor
		self.type = event_type
	
def customerCreated(user, customer_id=None, processor=None):
	return CustomerEvent(user, CUSTOMER_CREATED, customer_id, processor)

def customerDeleted(user, customer_id=None, processor=None):
	return CustomerEvent(user, CUSTOMER_DELETED, customer_id, processor)

class ICustomer(interface.Interface):
	
	def getCustomerId(processor):
		"""
		return the customer id associated w/ the specified processor
		"""
		
	def setCustomerId(processor, customer_id):
		"""
		Store the the customer id associated w/ the specified processor
		"""
		
	def removeCustomerId(processor):
		"""
		Remove the the customer id associated w/ the specified processor
		"""
		
	def registerTransaction(trx):
		"""
		register the transction w/ this customer
		"""
	
	def completeTransaction(trx, new_trx_id=None):
		"""
		register the completion of a transaction
		
		:state Transaction state
		:new_trx_id New transaction id (if any)
		"""
		
	def removeTransaction(trx):
		"""
		unregister the transaction
		"""
		
	def getTransaction(trxid):
		"""
		return the transaction with the specified id
		"""	
		
	def getTransactionState(trxid):
		"""
		return the state of the specified transaction
		"""	
	
		