from __future__ import unicode_literals, print_function, absolute_import

import six
import time
from datetime import datetime

from zope import interface
from zope.event import notify
from zope.container import contained as zcontained
from zope.annotation import interfaces as an_interfaces

from persistent import Persistent

from nti.dataserver.users import User
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.datastructures import ModDateTrackingObject

from . import interfaces as store_interfaces

@interface.implementer(store_interfaces.IPurchaseAttempt, an_interfaces.IAttributeAnnotatable)
class PurchaseAttempt(zcontained.Contained, ModDateTrackingObject, Persistent):
	
	end_time = None
	failure_code = None
	failure_message = None
	
	def __init__(self, items, processor, state, start_time=None, end_time=None,
				 failure_code=None, failure_message=None):
		
		self.state = state
		self.processor = processor
		self.start_time = start_time if start_time else time.time()
		self.items = frozenset([items]) if isinstance(items, six.string_types) else items			
		if end_time is not None:
			self.end_time = end_time
		if failure_code:
			self.failure_code = failure_code
		if failure_message:
			self.failure_message = failure_message
	
	def __repr__( self ):
		d = datetime.fromtimestamp(self.start_time)
		return "%s(%s,%s,%s)" % (self.__class__, self.state, d, self.items)
	
	def __eq__( self, other ):
		return self is other or (isinstance(other, PurchaseAttempt) 
								 and self.processor == other.processor 
								 and self.start_time == other.start_time
								 and self.items == other.items)

	def __hash__( self ):
		xhash = 47
		xhash ^= hash(self.processor)
		xhash ^= hash(self.start_time)
		xhash ^= hash(self.items)
		return xhash
	
	def has_completed(self):
		return self.state in (store_interfaces.PA_STATE_FAILED, store_interfaces.PA_STATE_SUCCESSFUL)
	
	def has_failed(self):
		return self.state in (store_interfaces.PA_STATE_FAILED)
		
	def has_succeeded(self):
		return self.state in (store_interfaces.PA_STATE_SUCCESSFUL)
	
	def is_pending(self):
		return self.state in (store_interfaces.PA_STATE_STARTED, store_interfaces.PA_STATE_PENDING)
	
def create_purchase_attempt(items, processor, state=store_interfaces.PA_STATE_STARTED, start_time=None):
	state = state or store_interfaces.PA_STATE_UNKNOWN
	items = frozenset() if not items else items	
	items = frozenset([items]) if isinstance(items, six.string_types) else frozenset(items)	
	return PurchaseAttempt(items, processor, state=state, start_time=start_time)

def create_purchase_attempt_and_start(user, items, processor, start_time=None):	
	result = create_purchase_attempt(items, processor, state=store_interfaces.PA_STATE_STARTED, start_time=start_time)
	user = User.get_user(str(user)) if not nti_interfaces.IUser.providedBy(user) else user
	notify(store_interfaces.PurchaseAttemptStarted(result, user))
	return result
