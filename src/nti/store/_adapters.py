from __future__ import unicode_literals, print_function, absolute_import

import time
import struct
import BTrees

from zope import component
from zope import interface
from zope import lifecycleevent 
from zope.annotation import factory as an_factory

from persistent import Persistent

from nti.dataserver import interfaces as nti_interfaces

from . import interfaces as store_interfaces

def _time_to_64bit_int( value ):
	return struct.unpack( b'!Q', struct.pack( b'!d', value ) )[0]

@component.adapter(nti_interfaces.IUser)
@interface.implementer( store_interfaces.IPurchaseHistory)
class _PurchaseHistory(Persistent):
	
	family = BTrees.family64
	
	def __init__(self):
		self.time_map = self.family.IO.BTree()
		self.purchases = self.family.OO.BTree()
		
	def add_purchase(self, purchase):
		start_time = purchase.start_time
		self.time_map[_time_to_64bit_int(start_time)] = purchase.id
		self.purchases[purchase.id]= purchase
	
	register_purchase = add_purchase
		
	def _remove(self, pid, start_time=None):
		if start_time:
			self.time_map.pop(_time_to_64bit_int(start_time), None)
		result = self.purchases.pop(pid, None)
		if result: lifecycleevent.removed(result)
		return result
		
	def remove_purchase(self, purchase):
		start_time = purchase.start_time
		return self._remove(purchase.id, start_time)
		
	def get_purchase(self, pid):
		return self.purchases.get(pid, None)
		
	def get_purchase_state(self, pid):
		p = self.get_purchase(pid)
		return p.state if p else None
	
	def values(self):
		for p in self.purchases.values():
			yield p
	
def _PurchaseHistoryFactory(user):
	result = an_factory(_PurchaseHistory)(user)
	return result

@component.adapter(store_interfaces.IPurchaseAttempt, store_interfaces.IPurchaseAttemptStarted)
def _purchase_attempt_started( purchase, event ):
	purchase.state = store_interfaces.PA_STATE_STARTED
	hist = store_interfaces.IPurchaseHistory(event.user)
	hist.register_purchase(purchase)
	
@component.adapter(store_interfaces.IPurchaseAttempt, store_interfaces.IPurchaseAttemptSuccessful)
def _purchase_attempt_successful( purchase, event  ):
	purchase.state = store_interfaces.PA_STATE_SUCCESSFUL
	purchase.end_time = time.time()

@component.adapter(store_interfaces.IPurchaseAttempt, store_interfaces.IPurchaseAttemptFailed)
def _purchase_attempt_failed( purchase, event  ):
	purchase.state = store_interfaces.PA_STATE_FAILED
	purchase.end_time = time.time()
	purchase.failure_code = event.failure_code
	purchase.failure_message = event.failure_message
