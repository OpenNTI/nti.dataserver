# -*- coding: utf-8 -*-
"""
Defines purchase history.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import BTrees
from BTrees.OOBTree import OOTreeSet

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
from . import interfaces as store_interfaces
from .purchase_attempt import create_purchase_attempt

@component.adapter(nti_interfaces.IUser)
@interface.implementer(store_interfaces.IPurchaseHistory)
class PurchaseHistory(zcontained.Contained, Persistent):

	family = BTrees.family64

	def __init__(self):
		self.items_purchased = OOTreeSet()
		self.purchases = self.family.IO.BTree()

	@property
	def user(self):
		return self.__parent__

	def register_purchased_items(self, items):
		items = to_frozenset(items)
		self.items_purchased.update(items)

	def remove_purchased_items(self, items):
		count = 0
		items = to_frozenset(items)
		for item in items:
			if item in self.items_purchased:
				count += 1
				self.items_purchased.remove(item)
		return count

	def is_item_purchased(self, item):
		return item in self.items_purchased

	def register_purchase(self, purchase):
		start_time = purchase.StartTime
		self.purchases[time_to_64bit_int(start_time)] = purchase
		locate(purchase, self, repr(purchase))
		lifecycleevent.added(purchase)

	add_purchase = register_purchase

	def remove_purchase(self, purchase):
		if self.purchases.pop(time_to_64bit_int(purchase.StartTime), None):
			self.remove_purchased_items(purchase.Items)
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
		for p in self.purchases.values():
			if p.is_pending() or p.is_unknown():
				yield p

	def get_pending_purchase_for(self, items):
		items = to_frozenset(items)
		for p in self.purchases.values():
			if (p.is_pending() or p.is_unknown()) and p.Items.intersection(items):
				return p
		return None

	def get_purchase_history(self, start_time=None, end_time=None):
		start_time = time_to_64bit_int(start_time) if start_time is not None else None
		end_time = time_to_64bit_int(end_time) if end_time is not None else None
		return self.purchases.iteritems(start_time, end_time)  # iter inclusively between the two times; None is ignored

	def values(self):
		return self.purchases.values()  # BTree values() is lazy

	def __iter__(self):
		return iter(self.purchases.values())  # BTree values() is lazy

	def __len__(self):
		# JAM: FIXME: We should be caching a Length object,
		# as this is otherwise an expensive thing to do. If we
		# do not define __nonzero__/__bool__, then this gets
		# invoked a lot. OTOH, if length is not a particularly useful
		# concept for us, we should not define this method
		return len(self.purchases)

	def __nonzero__(self):
		return True
	__bool__ = __nonzero__

_PurchaseHistoryFactory = an_factory(PurchaseHistory)

def _get_user(user):
	if user is not None:
		user = User.get_user(str(user)) if not nti_interfaces.IUser.providedBy(user) else user
	return user

def register_purchased_items(user, items):
	user = _get_user(user)
	hist = store_interfaces.IPurchaseHistory(user)
	hist.register_purchased_items(items)

def remove_purchased_items(user, items):
	user = _get_user(user)
	hist = store_interfaces.IPurchaseHistory(user)
	return hist.remove_purchased_items(items)

def is_item_purchased(user, item):
	user = _get_user(user)
	hist = store_interfaces.IPurchaseHistory(user)
	return hist.is_item_purchased(item)

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

def create_and_register_purchase_attempt(username, items, processor, quantity=None, state=None, description=None, start_time=None):
	user = _get_user(username)
	purchase = create_purchase_attempt(items=items, processor=processor, quantity=quantity,
									   state=state, description=description, start_time=start_time)
	return register_purchase_attempt(purchase, user)
