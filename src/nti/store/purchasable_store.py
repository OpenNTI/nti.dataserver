# -*- coding: utf-8 -*-
"""
Purchasable store helper methods

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import six

from zope import interface

from zope.schema import interfaces as sch_interfaces
from zope.componentvocabulary.vocabulary import UtilityNames
from zope.componentvocabulary.vocabulary import UtilityVocabulary

from nti.dataserver.users import User
from nti.dataserver import interfaces as nti_interfaces

from . import purchasable
from .utils import to_collection
from . import interfaces as store_interfaces

@interface.provider(sch_interfaces.IVocabularyFactory)
class PurchasableTokenVocabulary(object, UtilityNames):

	def __init__(self, context=None):
		UtilityNames.__init__(self, store_interfaces.IPurchasable)

class PurchasableUtilityVocabulary(UtilityVocabulary):
	interface = store_interfaces.IPurchasable

class PurchasableNameVocabulary(PurchasableUtilityVocabulary):
	nameOnly = True

def get_available_items(user):
	"""
	Return all item that can be purchased
	"""
	util = PurchasableUtilityVocabulary(None)
	all_ids = set([p.value.NTIID for p in util])

	# get purchase history
	purchased = set()
	user = User.get_user(str(user)) if not nti_interfaces.IUser.providedBy(user) else user
	history = store_interfaces.IPurchaseHistory(user)
	for p in history:
		if p.has_succeeded() or p.is_pending():
			purchased.update(p.Items)

	available = all_ids - purchased
	result = {k:util.getTermByToken(k).value for k in available}
	return result

def get_content_items(purchased_items):
	"""
	return the nttids of the library items that were purchased
	"""
	if isinstance(purchased_items, six.string_types):
		purchased_items = to_collection(purchased_items)

	result = set()
	util = PurchasableUtilityVocabulary(None)
	for item in purchased_items:
		try:
			p = util.getTermByToken(item).value
			result.update(p.Items)
		except:
			pass
	return result

create_purchasable = purchasable.create_purchasable
