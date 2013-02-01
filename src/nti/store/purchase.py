from __future__ import unicode_literals, print_function, absolute_import

import six
import time
import uuid

from zope import interface

from persistent import Persistent

from . import interfaces as store_interfaces

@interface.implementer( store_interfaces.IPurchaseAttempt)
class PurchaseAttempt(Persistent):
	
	end_time = None
	failure_code = None
	failure_message = None
	
	def __init__(self, purchase_id, items, processor, state, start_time=None, end_time=None,
				 failure_code=None, failure_message=None):
		
		self.state = state
		self.id = str(uuid.uuid4())
		self.processor = processor
		self.purchase_id = purchase_id
		self.start_time = start_time if start_time else time.time()
		self.items = frozenset([items]) if isinstance(items, six.string_types) else items			
		if not end_time:
			self.end_time = end_time
		if not failure_code:
			self.failure_code = failure_code
		if not failure_message:
			self.failure_message = failure_message
		
	def __str__( self ):
		return "%s,%s" % (self.purchase_id, self.state)

	def __repr__( self ):
		return "%s(%s,%s,%s,%s)" % (self.__class__, self.id, self.purchase_id, self.state, self.items)
	
	def __eq__( self, other ):
		return self is other or (isinstance(other, PurchaseAttempt) and self.id == other.id)
	
	def __hash__(self):
		return hash(self.id)
	
	def has_completed(self):
		return self.state in (store_interfaces.PA_STATE_FAILED, store_interfaces.PA_STATE_SUCCESSFUL)
	
	def has_failed(self):
		return self.state in (store_interfaces.PA_STATE_FAILED)
		
	def has_succeeded(self):
		return self.state in (store_interfaces.PA_STATE_SUCCESSFUL)
	
	def is_pending(self):
		return self.state in (store_interfaces.PA_STATE_STARTED, store_interfaces.PA_STATE_PENDING)
	
def create_purchase_attempt(purchase_id, items, processor, state=store_interfaces.PA_STATE_STARTED, start_time=None):
	state = state or store_interfaces.PA_STATE_UNKNOWN
	items = frozenset() if not items else items	
	return PurchaseAttempt(purchase_id, items, processor, state=state, start_time=start_time)