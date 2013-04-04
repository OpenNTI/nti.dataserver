# -*- coding: utf-8 -*-
"""
Purchasable store helper methods

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import component

from nti.dataserver.users import User
from nti.dataserver import interfaces as nti_interfaces

from . import interfaces as store_interfaces

def get_purchasables():
	utils = component.getUtilitiesFor(store_interfaces.IPurchasable)
	result = {k:v for  k, v in utils}
	return result

def get_available_items(store, user):
	# gather all item that can be purchased
	purchasables = get_purchasables()
	all_ids = set(purchasables.keys())

	# get purchase history
	user = User.get_user(str(user)) if not nti_interfaces.IUser.providedBy(user) else user
	history = store_interfaces.IPurchaseHistory(user)
	purchased = set()
	for p in history:
		purchased.update(p.Items)

	available = all_ids - purchased
	result = {k:purchasables.get(k) for k in available}
	return result
