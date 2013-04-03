# -*- coding: utf-8 -*-
"""
Defines Purchasable Store.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import BTrees

from zope import interface
from zope import lifecycleevent
from zope.location import locate
from zope.container import contained as zcontained

from persistent import Persistent

from nti.dataserver.users import User
from nti.dataserver import interfaces as nti_interfaces

from . import interfaces as store_interfaces

@interface.implementer(store_interfaces.IPurchasableStore)
class PurchasableStore(zcontained.Contained, Persistent):

	family = BTrees.family64

	def __init__(self):
		self.items = self.family.OO.BTree()

	def add(self, purchasable):
		ntiid = purchasable.NTTID
		self.items[ntiid] = purchasable
		locate(purchasable, self, str(purchasable))
		lifecycleevent.added(purchasable)

	def remove(self, purchasable):
		ntiid = purchasable
		if store_interfaces.IPurchasable.implementedBy(purchasable):
			ntiid = purchasable.NTTID

		item = self.items.pop(ntiid, None)
		if item is not None:
			lifecycleevent.removed(item)

	def get(self, ntiid):
		result = self.items.get(ntiid)
		return result

	def keys(self):
		return self.items.keys()

	def values(self):
		for p in self.items.values():
			yield p

	def __iter__(self):
		return iter(self.items.values())

	def __len__(self):
		return len(self.items)

def get_available_items(store, user):
	user = User.get_user(str(user)) if not nti_interfaces.IUser.providedBy(user) else user
	history = store_interfaces.IPurchaseHistory(user)
	all_ids = set(store.keys())
	purchased = set()
	for p in history:
		purchased.update(p.Items)
	return all_ids - purchased
