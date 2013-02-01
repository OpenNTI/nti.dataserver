from __future__ import unicode_literals, print_function, absolute_import

import struct
import BTrees

from zope import component
from zope import interface
from zope.annotation import factory as an_factory

from persistent import Persistent
from persistent.mapping import PersistentMapping

from nti.dataserver import interfaces as nti_interfaces

from . import interfaces as store_interfaces

def _time_to_64bit_int( value ):
	return struct.unpack( b'!Q', struct.pack( b'!d', value ) )[0]

@component.adapter(nti_interfaces.IUser)
@interface.implementer( store_interfaces.ICustomer)
class _Customer(Persistent):
	
	family = BTrees.family64
	
	def __init__(self):
		self.time_map = self.family.IO.BTree()
		self.transactions = self.family.IO.BTree()
		self.customer_ids = PersistentMapping()
		
	def _register(self, trx):
		start_time = trx.start_time
		self.time_map[_time_to_64bit_int(start_time)] = trx.transaction_id
		self.transactions[trx.transaction_id] = trx
		
	def registerTransaction(self, trx):
		result = True
		if trx.hasCompleted():
			result = self.completeTransaction(trx)
		elif trx.isPending():
			self._register(trx)
		else:
			result = False
		return result
			
	def completeTransaction(self, trx, new_trx_id=None):
		assert trx.hasCompleted()
		if new_trx_id and new_trx_id != trx.transaction_id:
			self.removeTransaction(trx)
			trx.transaction_id = new_trx_id
		self._register(trx)
		return True
	
	def removeTransaction(self, trx):
		start_time = trx.start_time
		self.time_map.pop(_time_to_64bit_int(start_time), None)
		return self.transactions.pop(trx.transaction_id, None)

	def getTransaction(self, trxid):
		return self.transactions.get(trxid, None)

	def getTransactionState(self, trxid):
		trx = self.getTransaction(trxid)
		return trx.state if trx else store_interfaces.TRX_UNKNOWN
	
	def values(self):
		for trx in self.transactions.values():
			yield trx
	
	def getCustomerId(self, processor):
		return self.customer_ids.get(processor, None)
	
	def setCustomerId(self, processor, customer_id):
		self.customer_ids[processor] = customer_id
		
	def removeCustomerId(self, processor):
		return self.customer_ids.pop(processor, None)
		
def _CustomerFactory(user):
	result = an_factory(_Customer)(user)
	return result


@component.adapter(store_interfaces.ITransactionEvent)
def _transaction_event( trax_event ):
	pass

@component.adapter(store_interfaces.ITransactionFailed)
def _transaction_failed( trax_event ):
	pass

@component.adapter(store_interfaces.ITransactionCompleted)
def _transaction_completed( trax_event ):
	pass
	