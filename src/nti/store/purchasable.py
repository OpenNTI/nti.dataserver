#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
Defines purchasable object and operations on them

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six

from zope import component
from zope import interface
from zope.cachedescriptors.property import Lazy
from zope.schema import interfaces as sch_interfaces
from zope.mimetype import interfaces as zmime_interfaces

from zope.componentvocabulary.vocabulary import UtilityNames
from zope.componentvocabulary.vocabulary import UtilityVocabulary

from nti.dataserver.users import User
from nti.dataserver import authorization
from nti.dataserver import authorization_acl as a_acl
from nti.dataserver import interfaces as nti_interfaces

from nti.externalization.externalization import make_repr
from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import LocatedExternalList

from nti.ntiids import interfaces as nid_interfaces

from nti.utils.schema import AdaptingFieldProperty
from nti.utils.schema import createDirectFieldProperties

from . import utils
from . import content_bundle
from . import interfaces as store_interfaces

@interface.provider(sch_interfaces.IVocabularyFactory)  # Provider or implementer?
class PurchasableTokenVocabulary(object, UtilityNames):

	def __init__(self, context=None):
		UtilityNames.__init__(self, store_interfaces.IPurchasable)

class PurchasableUtilityVocabulary(UtilityVocabulary):
	interface = store_interfaces.IPurchasable

class PurchasableNameVocabulary(PurchasableUtilityVocabulary):
	nameOnly = True

@interface.implementer(store_interfaces.IPurchasable,
					   nti_interfaces.IACLProvider,
					   zmime_interfaces.IContentTypeAware)
class Purchasable(content_bundle.ContentBundle):

	__metaclass__ = utils.MetaStoreObject

	# create all interface fields
	createDirectFieldProperties(store_interfaces.IPurchasable)

	# Override Description to adapt to a content fragment
	Description = AdaptingFieldProperty(store_interfaces.IPurchasable['Description'])

	__repr__ = make_repr()

	def __eq__(self, other):
		try:
			return self is other or self.NTIID == other.NTIID
		except AttributeError:
			return NotImplemented

	def __reduce__(self):
		raise TypeError()

	@Lazy
	def __acl__(self):
		return (a_acl.ace_allowing(nti_interfaces.EVERYONE_USER_NAME,
								   authorization.ACT_READ, self),)

def create_purchasable(ntiid, provider, amount, currency='USD', items=(), fee=None,
					   title=None, license_=None, author=None, description=None,
					   icon=None, thumbnail=None, discountable=False,
					   bulk_purchase=True):
	fee = float(fee) if fee is not None else None
	amount = float(amount) if amount is not None else amount
	items = utils.to_frozenset(items) if items else frozenset((ntiid,))
	result = Purchasable(NTIID=ntiid, Provider=provider, Title=title, Author=author,
						 Items=items, Description=description, Amount=amount,
						 Currency=currency, Fee=fee, License=license_,
						 Discountable=discountable, BulkPurchase=bulk_purchase,
						 Icon=icon, Thumbnail=thumbnail)
	return result

@interface.implementer(store_interfaces.IPurchasableStore)
class ZcmlPurchasableStore(object):

	@property
	def vocabulary(self):
		result = PurchasableUtilityVocabulary(None)
		return result

	def get_purchasable(self, pid):
		try:
			result = self.vocabulary.getTermByToken(pid) if pid else None
		except (LookupError, KeyError):
			result = None
		return result.value if result is not None else None

	def get_all_purchasables(self):
		for p in self.vocabulary:
			yield p.value

	def get_purchasable_ids(self):
		for p in self.vocabulary:
			yield p.value.NTIID

	def __len__(self):
		return len(self.vocabulary)

DefaultPurchasableStore = ZcmlPurchasableStore

def get_purchasable_store():
	return DefaultPurchasableStore()

def get_purchasable(pid, registry=component):
	result = get_purchasable_store().get_purchasable(pid)
	return result

def get_all_purchasables(registry=component):
	store = get_purchasable_store()
	result = LocatedExternalList(store.get_all_purchasables())
	return result

def get_available_items(user, registry=component):
	"""
	Return all item that can be purchased
	"""
	util = registry.queryUtility(store_interfaces.IPurchasableStore)
	all_ids = set(util.get_purchasable_ids()) if util else ()
	if not all_ids:
		return {}

	# get purchase history
	purchased = set()
	user = User.get_user(str(user))\
		   if not nti_interfaces.IUser.providedBy(user) else user
	history = store_interfaces.IPurchaseHistory(user)
	for p in history:
		if p.has_succeeded() or p.is_pending():
			purchased.update(p.Items)

	available = all_ids - purchased
	result = LocatedExternalDict({k:util.get_purchasable(k) for k in available})
	return result

def get_content_items(purchased_items, registry=component):
	"""
	return the nttids of the library items that were purchased
	"""
	if isinstance(purchased_items, six.string_types):
		purchased_items = utils.to_collection(purchased_items)

	result = set()
	store = get_purchasable_store()
	for item in purchased_items:
		p = store.get_purchasable(item)
		if p is not None:
			result.update(p.Items)
	return result

def get_providers(purchasables):
	result = {p.Provider for p in purchasables or ()}
	return sorted(result)

@interface.implementer(nid_interfaces.INTIIDResolver)
class _PurchasableResolver(object):

	def resolve(self, ntiid_string):
		return get_purchasable(ntiid_string)
