# -*- coding: utf-8 -*-
"""
Purchasable store helper methods

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import six
from zope import component

from nti.dataserver.users import User
from nti.dataserver import interfaces as nti_interfaces

from . import purchasable
from .utils import to_collection
from . import interfaces as store_interfaces

create_purchasable = purchasable.create_purchasable

def get_purchasables():
	utils = component.getUtilitiesFor(store_interfaces.IPurchasable)
	result = {k:v for  k, v in utils}
	return result

def get_available_items(store, user):
	"""
	Return all item that can be purchased
	"""
	purchasables = get_purchasables()
	all_ids = set(purchasables.keys())

	# get purchase history
	user = User.get_user(str(user)) if not nti_interfaces.IUser.providedBy(user) else user
	history = store_interfaces.IPurchaseHistory(user)
	purchased = set()
	for p in history:
		if not (p.has_succeeded() or p.is_pending()):
			purchased.update(p.Items)

	available = all_ids - purchased
	result = {k:purchasables.get(k) for k in available}
	return result

def get_content_items(purchased_items):
	"""
	return the nttids of the library items that were purchased
	"""
	if isinstance(purchased_items, six.string_types):
		purchased_items = to_collection(purchased_items)

	result = set()
	all_purchasables = get_purchasables()
	for item in purchased_items:
		p = all_purchasables.get(item)
		if p is not None:
			result.update(p.Items)
	return result
