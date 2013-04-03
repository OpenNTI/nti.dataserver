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

from . import to_frozenset
from . import interfaces as store_interfaces

def _time_to_64bit_int(value):
	return struct.unpack(b'!Q', struct.pack(b'!d', value))[0]

@component.adapter(nti_interfaces.IUser)
@interface.implementer(store_interfaces.IPurchaseHistory)
class PurchaseHistory(zcontained.Contained, Persistent):

	family = BTrees.family64

	def __init__(self):
		self.purchases = self.family.IO.BTree()

	@property
	def user(self):
		return self.__parent__

	def register_purchase(self, purchase):
		start_time = purchase.StartTime
		self.purchases[_time_to_64bit_int(start_time)] = purchase
		locate(purchase, self, repr(purchase))
		lifecycleevent.added(purchase)

	add_purchase = register_purchase

	def remove_purchase(self, purchase):
		if self.purchases.pop(_time_to_64bit_int(purchase.StartTime), None):
			lifecycleevent.removed(purchase)

	@classmethod
	def get_purchase(cls, pid):
		result = ntiids.find_object_with_ntiid(pid)
		return result

	def get_purchase_state(self, pid):
		p = self.get_purchase(pid)
		return p.State if p else None

	def get_pending_purchases(self):
		for p in self.purchases.values():
			if p.is_pending() or p.is_unknown():
				yield p

	def get_pending_purchase_for(self, items, on_behalf_of=None):
		items = to_frozenset(items)
		on_behalf_of = to_frozenset(on_behalf_of)
		for p in self.purchases.values():
			if (p.is_pending() or p.is_unknown()) and \
				p.Items.intersection(items) and \
				(not on_behalf_of or p.actors().intersection(on_behalf_of)):
				return p
		return None

	def get_purchase_history(self, start_time=None, end_time=None):
		start_time = _time_to_64bit_int(start_time or 0)
		end_time = _time_to_64bit_int(end_time or sys.maxint)
		for t, p in self.purchases.iteritems():
			if t > end_time:
				break
			elif t >= start_time and t <= end_time:
				yield p

	def values(self):
		for p in self.purchases.values():
			yield p

	def __iter__(self):
		return iter(self.purchases.values())

	def __len__(self):
		return len(self.purchases)

_PurchaseHistoryFactory = an_factory(PurchaseHistory)

def get_purchase_attempt(purchase_id, user=None):
	if user is not None:
		user = User.get_user(str(user)) if not nti_interfaces.IUser.providedBy(user) else user
	result = PurchaseHistory.get_purchase(purchase_id)
	if result is not None and user is not None:  # validate
		result = None if result.creator != user else result
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

def get_pending_purchase_for(user, items, on_behalf_of=None):
	user = User.get_user(str(user)) if not nti_interfaces.IUser.providedBy(user) else user
	hist = store_interfaces.IPurchaseHistory(user)
	result = hist.get_pending_purchase_for(items, on_behalf_of)
	return result

def register_purchase_attempt(username, purchase):
	assert getattr(purchase, '_p_oid', None) is None
	result = []
	def func():
		user = User.get_user(username)
		hist = store_interfaces.IPurchaseHistory(user)
		hist.register_purchase(purchase)
		result.append(purchase.id)
	component.getUtility(nti_interfaces.IDataserverTransactionRunner)(func)
	return result[0]
