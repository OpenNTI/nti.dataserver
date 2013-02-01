from __future__ import unicode_literals, print_function, absolute_import

import time

from zope import interface

from persistent import Persistent

from . import interfaces as store_interfaces

from nti.utils.property import alias

@interface.implementer( store_interfaces.ITransaction)
class Transaction(Persistent):
	
	end_time = None
	failure_code = None
	failure_message = None
	
	def __init__(self, trxid, processor, state, start_time=None, end_time=None,
				 failure_code=None, failure_message=None):
		
		self.state = state
		self.processor = processor
		self.transaction_id = trxid
		self.start_time = start_time if start_time else time.time()
		if not end_time:
			self.end_time = end_time
		if not failure_code:
			self.failure_code = failure_code
		if not failure_message:
			self.failure_message = failure_message
		
	trxid = alias('transaction_id')
	
	def hasCompleted(self):
		return self.state in (store_interfaces.TRX_FAILED, store_interfaces.TRX_SUCCESSFUL)
	
	def hasFailed(self):
		return self.state in (store_interfaces.TRX_FAILED)
		
	def hasSucceeded(self):
		return self.state in (store_interfaces.TRX_SUCCESSFUL)
	
	def isPending(self):
		return self.state in (store_interfaces.TRX_STARTED, store_interfaces.TRX_PENDING)
	
def create_transaction(trxid, processor, state=None, start_time=None):
	state = state or store_interfaces.TRX_UNKNOWN
	return Transaction(trxid, processor, state=state, start_time=start_time)