# -*- coding: utf-8 -*-
"""
Defines purchase history.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import sys
import struct
import BTrees

from zope import component
from zope import interface
from zope import lifecycleevent
from zope.location import locate
from zope.annotation import factory as an_factory
from zope.container import contained as zcontained

from persistent import Persistent

from nti.ntiids import ntiids

from nti.dataserver.users import User
from nti.dataserver import interfaces as nti_interfaces

from .purchase_attempt import to_frozenset 
from . import interfaces as store_interfaces

def _time_to_64bit_int( value ):
	return struct.unpack( b'!Q', struct.pack( b'!d', value ) )[0]

@component.adapter(nti_interfaces.IUser)
@interface.implementer( store_interfaces.IPurchaseHistory )
class _PurchaseHistory(zcontained.Contained, Persistent):

	family = BTrees.family64

	def __init__(self):
		self.time_map = self.family.IO.BTree()
		self.purchases = self.family.OO.OOTreeSet()

	@property
	def user(self):
		return self.__parent__

	def register_purchase(self, purchase):
		start_time = purchase.start_time
		self.time_map[_time_to_64bit_int(start_time)] = purchase
		self.purchases.add(purchase)
		locate(purchase, self, repr(purchase))
		lifecycleevent.added(purchase)

	add_purchase = register_purchase

	def remove_purchase(self, purchase):
		self.time_map.pop(_time_to_64bit_int(purchase.start_time), None)
		try:
			self.purchases.remove(purchase)
			lifecycleevent.removed(purchase)
		except:
			pass

	def get_purchase(self, pid):
		result = ntiids.find_object_with_ntiid(pid )
		return result

	def get_purchase_state(self, pid):
		p = self.get_purchase(pid)
		return p.State if p else None

	def get_pending_purchases(self):
		for p in self.time_map.values():
			if p.is_pending() or p.is_unknown():
				yield p
	
	def get_pending_purchase_for(self, items):
		items = to_frozenset(items) 
		for p in self.time_map.values():
			if p.items.intersection(items) and (p.is_pending() or p.is_unknown()):
				return p
		return None

	def get_purchase_history(self, start_time=None, end_time=None):
		start_time = _time_to_64bit_int(start_time or 0)
		end_time = _time_to_64bit_int(end_time or sys.maxint)
		for t, p in self.time_map.iteritems():
			if t > end_time:
				break
			elif t >= start_time and t<= end_time:
				yield p

	def values(self):
		for p in self.time_map.values():
			yield p

	def __iter__(self):
		return iter(self.time_map.values())

	def __len__(self):
		return len(self.purchases)

_PurchaseHistoryFactory = an_factory(_PurchaseHistory)

def get_purchase_attempt(purchase_id, user):
	user = User.get_user(str(user)) if not nti_interfaces.IUser.providedBy(user) else user
	hist = store_interfaces.IPurchaseHistory(user)
	result = hist.get_purchase(purchase_id)
	result = None if result is None or result.creator != user else result
	return result

def get_pending_purchases(user):
	user = User.get_user(str(user)) if not nti_interfaces.IUser.providedBy(user) else user
	hist = store_interfaces.IPurchaseHistory(user)
	result = list(hist.get_pending_purchases())
	return result

def get_purchase_history(user, start_time=None, end_time=None):
	user = User.get_user(str(user)) if not nti_interfaces.IUser.providedBy(user) else user
	hist = store_interfaces.IPurchaseHistory(user)
	result = list(hist.get_purchase_history(start_time, end_time))
	return result

def get_pending_purchase_for(user, items):
	items = to_frozenset(items) 
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
