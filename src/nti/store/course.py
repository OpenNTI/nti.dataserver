#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
Defines course object and operations on them

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import interface

from nti.ntiids import interfaces as nid_interfaces

from nti.utils.schema import AdaptingFieldProperty
from nti.utils.schema import createDirectFieldProperties

from . import purchasable
from . import to_frozenset
from . import interfaces as store_interfaces

@interface.implementer(store_interfaces.ICourse)
class Course(purchasable.Purchasable):
	createDirectFieldProperties(store_interfaces.ICourse)
	Description = AdaptingFieldProperty(store_interfaces.IPurchasable['Description'])

	def __repr__(self):
		return "%s(%s,%s)" % (self.__class__, self.Description, self.NTIID)

	def __eq__(self, other):
		try:
			return self is other or (store_interfaces.ICourse.providedBy(other)
									 and self.NTIID == other.NTIID)
		except AttributeError:
			return NotImplemented

def create_course(ntiid, name=None, provider=None, amount=None, currency=None, items=(), fee=None, title=None,
				  license_=None, author=None, description=None, icon=None, thumbnail=None, discountable=False,
				  bulk_purchase=False, communities=(), featured=False):
	if amount and not provider:
		raise AssertionError("Must specfify a provider")

	if amount and not currency:
		raise AssertionError("Must specfify a currency")

	fee = float(fee) if fee is not None else None
	amount = float(amount) if amount is not None else amount
	communities = to_frozenset(communities) if items else None
	items = to_frozenset(items) if items else frozenset((ntiid,))

	result = Course(NTIID=ntiid, Name=name, Provider=provider, Title=title, Author=author,
					Items=items, Description=description, Amount=amount, Currency=currency,
					Fee=fee, License=license_, Discountable=discountable, BulkPurchase=bulk_purchase,
				 	Icon=icon, Thumbnail=thumbnail, Communities=communities, Featured=featured)

	return result

@interface.implementer(nid_interfaces.INTIIDResolver)
class _CourseResolver(object):

	def resolve(self, ntiid_string):
		return purchasable.get_purchasable(ntiid_string)

def get_course(course_id):
	result = purchasable.get_purchasable(course_id)
	return result
