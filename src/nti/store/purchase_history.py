from __future__ import unicode_literals, print_function, absolute_import

import time
import struct
import BTrees

import zope.intid
from zope import component
from zope import interface
from zope import lifecycleevent 
from zope.location import locate
from zope.location.interfaces import ILocation
from zope.annotation import factory as an_factory

from persistent import Persistent

from nti.ntiids import ntiids
from nti.dataserver import interfaces as nti_interfaces

from . import interfaces as store_interfaces

logger = __import__('logging').getLogger( __name__ )

def _time_to_64bit_int( value ):
	return struct.unpack( b'!Q', struct.pack( b'!d', value ) )[0]

@component.adapter(nti_interfaces.IUser)
@interface.implementer( store_interfaces.IPurchaseHistory, ILocation)
class _PurchaseHistory(Persistent):
	
	family = BTrees.family64
	
	def __init__(self):
		self.time_map = self.family.IO.BTree()
		self.purchases = self.family.OO.OOTreeSet()

	@property
	def user(self):
		return self.__parent__
			
	def register_purchase(self, purchase):
		
		# ensure there is a OID
		if self._p_jar:
			self._p_jar.add(purchase)
		elif self.user._p_jar:
			self.user._p_jar.add(purchase)
			
		# add to map(s)
		start_time = purchase.start_time
		self.time_map[_time_to_64bit_int(start_time)] = purchase
		self.purchases.add(purchase)
		locate(purchase, repr(purchase))
		
		# register w/ intids
		intids = component.queryUtility( zope.intid.IIntIds )
		intids.register( purchase )
	
	add_purchase = register_purchase
		
	def remove_purchase(self, purchase):
		intids = component.queryUtility( zope.intid.IIntIds )
		self.time_map.pop(_time_to_64bit_int(purchase.start_time), None)
		try:
			self.purchases.remove(purchase)
			intids.unregister(purchase)
			lifecycleevent.removed(purchase)
		except:
			pass
		
	def get_purchase(self, pid):
		result = ntiids.find_object_with_ntiid(pid )
		return result
		
	def get_purchase_state(self, pid):
		p = self.get_purchase(pid)
		return p.State if p else None
	
	def values(self):
		for p in self.purchases.values():
			yield p
	
	def __len__(self):
		return len(self.purchases)
	
	def __iter(self):
		return iter(self.purchases)
	
def _PurchaseHistoryFactory(user):
	result = an_factory(_PurchaseHistory)(user)
	return result


def _trx_runner(f, retries=5, sleep=0.1):
	trxrunner = component.getUtility(nti_interfaces.IDataserverTransactionRunner)
	trxrunner(f, retries=5, sleep=0.1)
	
@component.adapter(store_interfaces.IPurchaseAttempt, store_interfaces.IPurchaseAttemptStarted)
def _purchase_attempt_started( purchase, event ):
	def func():
		purchase.updateLastMod()
		purchase.State = store_interfaces.PA_STATE_STARTED
		user = event.user
		hist = store_interfaces.IPurchaseHistory(user)
		hist.register_purchase(purchase)
		logger.info('%s started %s' % (user, purchase))
	_trx_runner(func)
	
@component.adapter(store_interfaces.IPurchaseAttempt, store_interfaces.IPurchaseAttemptSuccessful)
def _purchase_attempt_successful( purchase, event  ):
	def func():
		purchase.State = store_interfaces.PA_STATE_SUCCESSFUL
		purchase.EndTime = time.time()
		purchase.updateLastMod()
		logger.info('%s completed successfully' % (purchase))
	_trx_runner(func)

@component.adapter(store_interfaces.IPurchaseAttempt, store_interfaces.IPurchaseAttemptRefunded)
def _purchase_attempt_refunded( purchase, event  ):
	def func():
		purchase.State = store_interfaces.PA_STATE_REFUNDED
		purchase.EndTime = time.time()
		purchase.updateLastMod()
		logger.info('%s has been refunded' % (purchase))
	_trx_runner(func)
	
@component.adapter(store_interfaces.IPurchaseAttempt, store_interfaces.IPurchaseAttemptFailed)
def _purchase_attempt_failed( purchase, event  ):
	def func():
		purchase.updateLastMod()
		purchase.EndTime = time.time()
		purchase.State = store_interfaces.PA_STATE_FAILED
		if event.error_code:
			purchase.ErrorCode = event.error_code
		if event.error_message:
			purchase.ErrorMessage = event.error_message
		logger.info('%s failed. %s' % (purchase, event.error_message))
	_trx_runner(func)

@component.adapter(store_interfaces.IPurchaseAttempt, store_interfaces.IPurchaseAttemptSynced)
def _purchase_attempt_synced( purchase, event  ):
	def func():
		purchase.Synced = True
		logger.info('%s has been synched' % (purchase))
	_trx_runner(func)
