from __future__ import unicode_literals, print_function, absolute_import

import six
import time
from datetime import datetime

import persistent
from zope import interface
from zope.location import ILocation
from zope.container import contained as zcontained
from zope.annotation import interfaces as an_interfaces

from nti.dataserver.datastructures import ModDateTrackingObject

from nti.externalization.oids import to_external_ntiid_oid

from nti.utils.property import alias

from . import interfaces as store_interfaces

@interface.implementer(store_interfaces.IPurchaseAttempt, an_interfaces.IAttributeAnnotatable, ILocation)
class PurchaseAttempt(zcontained.Contained, ModDateTrackingObject, persistent.Persistent):
	
	Synced = False
	EndTime = None
	ErrorCode = None
	Description = None
	ErrorMessage = None
	
	def __init__(self, items, processor, state, description=None, start_time=None, end_time=None,
				 error_code=None, error_message=None, synced=False):
		
		self.State = state
		self.Processor = processor
		self.StartTime = start_time if start_time else time.time()
		self.Items = frozenset([items]) if isinstance(items, six.string_types) else items			
		if end_time is not None:
			self.EndTime = end_time
		if error_code:
			self.ErrorCode = error_code
		if error_message:
			self.ErorrMessage = error_message
		if description:
			self.Description = description
		if synced == True:
			self.Synced = True
	
	state = alias('State')
	items = alias('Items')
	synced = alias('Synced')
	processor = alias('Processor')
	start_time = alias('StartTime')
	description = alias('Description')

	@property
	def id(self):
		return unicode(to_external_ntiid_oid(self))
	
	def __repr__( self ):
		d = datetime.fromtimestamp(self.start_time)
		return "%s(%s,%s,%s)" % (self.__class__, self.state, d, self.items)
	
	def __eq__( self, other ):
		return self is other or (isinstance(other, PurchaseAttempt) 
								 and self.Processor == other.Processor 
								 and self.StartTime == other.StartTime
								 and self.Items == other.Items)

	def __hash__( self ):
		xhash = 47
		xhash ^= hash(self.Processor)
		xhash ^= hash(self.StartTime)
		xhash ^= hash(self.Items)
		return xhash
	
	def has_failed(self):
		return self.State == store_interfaces.PA_STATE_FAILED
		
	def has_succeeded(self):
		return self.State == store_interfaces.PA_STATE_SUCCESSFUL
	
	def is_pending(self):
		return self.State in (store_interfaces.PA_STATE_STARTED, store_interfaces.PA_STATE_PENDING)
	
	def is_refunded(self):
		return self.State == store_interfaces.PA_STATE_REFUNDED
	
	def is_disputed(self):
		return self.State == store_interfaces.PA_STATE_DISPUTED
	
	def is_reserved(self):
		return self.State == store_interfaces.PA_STATE_RESERVED
	
	def is_canceled(self):
		return self.State == store_interfaces.PA_STATE_CANCELED
	
	def has_completed(self):
		return not (self.is_pending() or self.is_reserved() or self.is_disputed())
	
	def is_synced(self):
		return self.Synced
	
def create_purchase_attempt(items, processor, state=store_interfaces.PA_STATE_UNKNOWN, description=None, start_time=None):
	items = frozenset() if not items else items	
	items = frozenset([items]) if isinstance(items, six.string_types) else frozenset(items)	
	return PurchaseAttempt(items=items, processor=processor, description=description, state=state, start_time=start_time)

