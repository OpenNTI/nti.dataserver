from __future__ import unicode_literals, print_function, absolute_import

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

from nti.dataserver.users import User
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
		locate(purchase, self, repr(purchase))
		lifecycleevent.added(purchase)
		
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

	def get_pending_purchase_for(self, items):
		for p in self.time_map.values():
			if p.items == items and (p.is_pending() or p.is_unknown()):
				return p
		return None
	
	def values(self):
		for p in self.time_map.values():
			yield p
	
	def __iter__(self):
		return iter(self.time_map.values())
	
	def __len__(self):
		return len(self.purchases)
	
	def __iter(self):
		return iter(self.purchases)
	
def _PurchaseHistoryFactory(user):
	result = an_factory(_PurchaseHistory)(user)
	return result

def get_purchase_attempt(purchase_id, user):
	user = User.get_user(str(user)) if not nti_interfaces.IUser.providedBy(user) else user
	hist = store_interfaces.IPurchaseHistory(user)
	result = hist.get_purchase(purchase_id)
	result = None if result is None or result.creator != user else result
	return result

def get_pending_purchase_for(user, items):
	user = User.get_user(str(user)) if not nti_interfaces.IUser.providedBy(user) else user
	hist = store_interfaces.IPurchaseHistory(user)
	result = hist.get_pending_purchase_for(items)
	return result

def register_purchase_attempt(username, purchase):
	assert getattr( purchase, '_p_oid', None ) is None
	result = []
	def func():
		user = User.get_user(username)
		hist = store_interfaces.IPurchaseHistory(user)
		hist.register_purchase(purchase)
		result.append(purchase.id)
	component.getUtility(nti_interfaces.IDataserverTransactionRunner)(func) 
	return result[0]

