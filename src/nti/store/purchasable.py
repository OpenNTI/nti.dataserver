# -*- coding: utf-8 -*-
"""
Defines purchasable object and operations on them

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import six

from zope import interface
from zope.cachedescriptors.property import Lazy
from zope.annotation import interfaces as an_interfaces
from zope.mimetype import interfaces as zmime_interfaces

from zope.schema import interfaces as sch_interfaces

from zope.componentvocabulary.vocabulary import UtilityNames
from zope.componentvocabulary.vocabulary import UtilityVocabulary

from nti.dataserver.users import User
from nti.dataserver import authorization
from nti.dataserver import authorization_acl as a_acl
from nti.dataserver import interfaces as nti_interfaces

from nti.externalization.datastructures import LocatedExternalList
from nti.externalization.datastructures import LocatedExternalDict

from nti.ntiids import interfaces as nid_interfaces

from nti.utils.schema import SchemaConfigured
from nti.utils.schema import AdaptingFieldProperty
from nti.utils.schema import createDirectFieldProperties

from . import to_frozenset
from . import interfaces as store_interfaces
from .utils import MetaStoreObject, to_collection

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
					   an_interfaces.IAttributeAnnotatable,
					   zmime_interfaces.IContentTypeAware)
class Purchasable(SchemaConfigured):

	__metaclass__ = MetaStoreObject

	# create all interface fields
	createDirectFieldProperties(store_interfaces.IPurchasable)

	# Override Description to adapt to a content fragment
	Description = AdaptingFieldProperty(store_interfaces.IPurchasable['Description'])

	@property
	def id(self):
		return self.NTIID

	def __str__(self):
		return self.NTIID

	def __repr__(self):
		return "%s(%s,%s,%s,%s)" % (self.__class__, self.Description, self.NTIID, self.Currency, self.Amount)

	def __eq__(self, other):
		try:
			return self is other or (store_interfaces.IPurchasable.providedBy(other)
									 and self.NTIID == other.NTIID)
		except AttributeError:
			return NotImplemented

	def __hash__(self):
		xhash = 47
		xhash ^= hash(self.NTIID)
		return xhash

	def __reduce__(self):
		raise TypeError()

	@Lazy
	def __acl__(self):
		return (a_acl.ace_allowing(nti_interfaces.EVERYONE_USER_NAME, authorization.ACT_READ, self),)

def create_purchasable(ntiid, provider, amount, currency='USD', items=(), fee=None, title=None,
					   author=None, description=None, icon=None, emails=(), discountable=False, bulk_purchase=True):
	fee = float(fee) if fee is not None else None
	emails = to_frozenset(emails) if emails else frozenset()
	items = to_frozenset(items) if items else frozenset((ntiid,))
	result = Purchasable(NTIID=ntiid, Provider=provider, Title=title, Author=author, Items=items,
						 Description=description, Amount=float(amount), Currency=currency, Fee=fee,
						 Discountable=discountable, BulkPurchase=bulk_purchase, Icon=icon, Emails=emails)
	return result

def get_purchasable(pid):
	"""
	Return purchasable with the specified id
	"""
	util = PurchasableUtilityVocabulary(None)
	try:
		result = util.getTermByToken(pid) if pid else None
	except (LookupError, KeyError):
		result = None
	return result.value if result is not None else None

def get_all_purchasables():
	"""
	Return all purchasable items
	"""
	result = LocatedExternalList()
	util = PurchasableUtilityVocabulary(None)
	for p in util:
		result.append(p.value)
	return result

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
	result = LocatedExternalDict({k:util.getTermByToken(k).value for k in available})
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
		except (LookupError, KeyError):
			pass
	return result

def get_providers(purchasables):
	result = set()
	for p in purchasables or ():
		result.add(p.Provider)
	return list(result)

@interface.implementer(nid_interfaces.INTIIDResolver)
class _PurchasableResolver(object):

	def resolve(self, ntiid_string):
		return get_purchasable(ntiid_string)
