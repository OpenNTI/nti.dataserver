# -*- coding: utf-8 -*-
"""
Defines Purchasable Store.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from nti.dataserver.users import User
from nti.dataserver import interfaces as nti_interfaces

from . import interfaces as store_interfaces

def get_available_items(store, user):
	user = User.get_user(str(user)) if not nti_interfaces.IUser.providedBy(user) else user
	history = store_interfaces.IPurchaseHistory(user)
	all_ids = set(store.keys())
	purchased = set()
	for p in history:
		purchased.update(p.Items)
	return all_ids - purchased
