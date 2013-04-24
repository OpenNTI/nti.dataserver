# -*- coding: utf-8 -*-
"""
Defines purchase history.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import BTrees
from BTrees.Length import Length

import zope.intid
from zope import component
from zope import interface
from zope import lifecycleevent
from zope.location import locate
from zope.annotation import factory as an_factory
from zope.container import contained as zcontained

from persistent import Persistent

from nti.externalization.datastructures import LocatedExternalList

from nti.ntiids import ntiids

from nti.dataserver.users import User
from nti.dataserver import interfaces as nti_interfaces

from nti.zodb.containers import time_to_64bit_int

from . import to_frozenset
from . import purchase_attempt
from . import interfaces as store_interfaces

class _PurchaseIndex(Persistent):

	family = BTrees.family64

	def __init__(self):
		self.__len = Length()
		self.purchases = self.family.II.LLTreeSet()
		self.item_index = self.family.OO.OOBTree()
		self.time_index = self.family.II.LLBTree()

	def add(self, purchase):
		iid = component.getUtility(zope.intid.IIntIds).getId(purchase)
		# main index
		self.purchases.add(iid)
		self.__len.change(1)
		# time index
		start_time = time_to_64bit_int(purchase.StartTime)
		self.time_index[start_time] = iid
		# item index
		for item in purchase.Items:
			item_set = self.item_index.get(item)
			if item_set is None:
				item_set = self.item_index[item] = self.family.II.LLTreeSet()
			item_set.add(iid)

	def remove(self, purchase):
		iid = component.getUtility(zope.intid.IIntIds).getId(purchase)
		if iid in self.purchases:
			self.__len.change(-1)
			self.purchases.remove(iid)
			self.time_index.pop(time_to_64bit_int(purchase.StartTime))
			for item in purchase.Items:
				item_set = self.item_index.get(item)
				if item_set and item_set.has_key(iid):
					item_set.remove(iid)
			return True
		return False

	def get_history_by_item(self, purchasabe_id):
		item_set = self.item_index.get(purchasabe_id)
		for iid in item_set or ():
			p = component.getUtility(zope.intid.IIntIds).queryObject(iid)
			if store_interfaces.IPurchaseAttempt.providedBy(p):
				yield p

	def get_history_by_time(self, start_time=None, end_time=None):
		start_time = time_to_64bit_int(start_time) if start_time is not None else None
		end_time = time_to_64bit_int(end_time) if end_time is not None else None
		for _, iid in self.time_index.iteritems(start_time, end_time):
			p = component.getUtility(zope.intid.IIntIds).queryObject(iid)
			if store_interfaces.IPurchaseAttempt.providedBy(p):
				yield p

	def values(self):
		for iid in self.purchases:
			p = component.getUtility(zope.intid.IIntIds).queryObject(iid)
			if store_interfaces.IPurchaseAttempt.providedBy(p):
				yield p

	def __iter__(self):
		return self.values()

	def __len__(self):
		return self.__len.value

	def __nonzero__(self):
		return True
	__bool__ = __nonzero__

	def _v_check(self):
		import BTrees.check
		self.purchases._check()
		self.item_index._check()
		self.time_index._check()
		BTrees.check.check(self.purchases)
		BTrees.check.check(self.item_index)
		BTrees.check.check(self.time_index)

@component.adapter(nti_interfaces.IUser)
@interface.implementer(store_interfaces.IPurchaseHistory)
class PurchaseHistory(zcontained.Contained, Persistent):

	family = BTrees.family64

	def __init__(self):
		self._index = _PurchaseIndex()
		self._items_activated = self.family.OO.OOTreeSet()

	@property
	def user(self):
		return self.__parent__

	def activate_items(self, items):
		items = to_frozenset(items)
		self._items_activated.update(items)

	def deactivate_items(self, items):
		count = 0
		items = to_frozenset(items)
		for item in items:
			if item in self._items_activated:
				count += 1
				self._items_activated.remove(item)
		return count

	def is_item_activated(self, item):
		return item in self._items_activated

	def register_purchase(self, purchase):
		locate(purchase, self, repr(purchase))
		lifecycleevent.added(purchase)
		self._index.add(purchase)

	add_purchase = register_purchase

	def remove_purchase(self, purchase):
		if self._index.remove(purchase):
			lifecycleevent.removed(purchase)
			return True
		return False

	@classmethod
	def get_purchase(cls, pid):
		result = ntiids.find_object_with_ntiid(pid)
		return result

	def get_purchase_state(self, pid):
		p = self.get_purchase(pid)
		return p.State if p else None

	def get_pending_purchases(self):
		for p in self.values():
			if p.is_pending() or p.is_unknown():
				yield p

	def get_pending_purchase_for(self, items):
		items = to_frozenset(items)
		for p in self.values():
			if (p.is_pending() or p.is_unknown()) and p.Items.intersection(items):
				return p
		return None

	def get_purchase_history_by_item(self, item):
		return self._index.get_history_by_item(item)

	def get_purchase_history(self, start_time=None, end_time=None):
		return self._index.get_history_by_time(start_time, end_time)

	def values(self):
		return self._index.values()

	def __iter__(self):
		return self._index.values()

	def __len__(self):
		return len(self._index)

	def _v_check(self):
		import BTrees.check
		self._index._v_check()
		self._items_activated._check()
		BTrees.check.check(self._items_activated)

_PurchaseHistoryFactory = an_factory(PurchaseHistory)

def _get_user(user):
	if user is not None:
		user = User.get_user(str(user)) if not nti_interfaces.IUser.providedBy(user) else user
	return user

def activate_items(user, items):
	user = _get_user(user)
	hist = store_interfaces.IPurchaseHistory(user)
	hist.activate_items(items)

def deactivate_items(user, items):
	user = _get_user(user)
	hist = store_interfaces.IPurchaseHistory(user)
	return hist.activate_items(items)

def is_item_activated(user, item):
	user = _get_user(user)
	hist = store_interfaces.IPurchaseHistory(user)
	return hist.is_item_activated(item)

def get_purchase_attempt(purchase_id, user=None):
	user = _get_user(user)
	result = PurchaseHistory.get_purchase(purchase_id)
	if result is not None and user is not None:  # validate
		result = None if result.creator != user else result
	return result

def remove_purchase_attempt(purchase, user):
	user = _get_user(user)
	hist = store_interfaces.IPurchaseHistory(user)
	return hist.remove_purchase(purchase)

def get_pending_purchases(user):
	user = _get_user(user)
	hist = store_interfaces.IPurchaseHistory(user)
	result = LocatedExternalList(hist.get_pending_purchases())
	return result

def get_purchase_history(user, start_time=None, end_time=None):
	user = _get_user(user)
	hist = store_interfaces.IPurchaseHistory(user)
	result = LocatedExternalList(hist.get_purchase_history(start_time, end_time))
	return result

def get_purchase_history_by_item(user, purchasable_id):
	user = _get_user(user)
	hist = store_interfaces.IPurchaseHistory(user)
	result = LocatedExternalList(hist.get_purchase_history_by_item(purchasable_id))
	return result

def get_pending_purchase_for(user, items):
	user = _get_user(user)
	hist = store_interfaces.IPurchaseHistory(user)
	result = hist.get_pending_purchase_for(items)
	return result

def register_purchase_attempt(purchase, user):
	user = _get_user(user)
	hist = store_interfaces.IPurchaseHistory(user)
	hist.register_purchase(purchase)
	return purchase.id

create_purchase_attempt = purchase_attempt.create_purchase_attempt
