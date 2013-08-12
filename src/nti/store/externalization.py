# -*- coding: utf-8 -*-
"""
Store externalization

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import urllib

from zope import interface
from zope import component
from zope.container.interfaces import ILocation

from pyramid.security import authenticated_userid
from pyramid.threadlocal import get_current_request

from nti.dataserver.links import Link

from nti.externalization import interfaces as ext_interfaces
from nti.externalization.singleton import SingletonDecorator
from nti.externalization.datastructures import InterfaceObjectIO

from nti.contentlibrary import interfaces as lib_interfaces

from . import invitations
from . import purchase_history
from .pyramid_views import DS_STORE_PATH
from . import interfaces as store_interfaces

LINKS = ext_interfaces.StandardExternalFields.LINKS

@interface.implementer(ext_interfaces.IInternalObjectIO)
@component.adapter(store_interfaces.IPurchaseItem)
class PurchaseItemExternal(InterfaceObjectIO):
	_ext_iface_upper_bound = store_interfaces.IPurchaseItem

@interface.implementer(ext_interfaces.IInternalObjectIO)
@component.adapter(store_interfaces.IPurchaseOrder)
class PurchaseOrderExternal(InterfaceObjectIO):
	_ext_iface_upper_bound = store_interfaces.IPurchaseOrder

@interface.implementer(ext_interfaces.IInternalObjectIO)
@component.adapter(store_interfaces.IPurchaseAttempt)
class PurchaseAttemptExternal(InterfaceObjectIO):
	_ext_iface_upper_bound = store_interfaces.IPurchaseAttempt

@interface.implementer(ext_interfaces.IInternalObjectIO)
@component.adapter(store_interfaces.IInvitationPurchaseAttempt)
class InvitationPurchaseAttemptExternal(InterfaceObjectIO):
	_ext_iface_upper_bound = store_interfaces.IInvitationPurchaseAttempt

@interface.implementer(ext_interfaces.IInternalObjectIO)
@component.adapter(store_interfaces.IRedeemedPurchaseAttempt)
class RedeemedPurchaseAttemptExternal(InterfaceObjectIO):
	_ext_iface_upper_bound = store_interfaces.IRedeemedPurchaseAttempt

@interface.implementer(ext_interfaces.IInternalObjectIO)
@component.adapter(store_interfaces.IPurchasable)
class PurchasableExternal(InterfaceObjectIO):
	_ext_iface_upper_bound = store_interfaces.IPurchasable

@interface.implementer(ext_interfaces.IInternalObjectIO)
@component.adapter(store_interfaces.IPriceable)
class PriceableExternal(InterfaceObjectIO):
	_ext_iface_upper_bound = store_interfaces.IPriceable

@interface.implementer(ext_interfaces.IInternalObjectIO)
@component.adapter(store_interfaces.IPricedItem)
class PricedItemExternal(InterfaceObjectIO):
	_ext_iface_upper_bound = store_interfaces.IPricedItem
	_excluded_out_ivars_ = InterfaceObjectIO._excluded_out_ivars_ | {'PurchaseFee'}

@interface.implementer(ext_interfaces.IInternalObjectIO)
@component.adapter(store_interfaces.IPricingResults)
class PricingResultsExternal(InterfaceObjectIO):
	_ext_iface_upper_bound = store_interfaces.IPricingResults
	_excluded_out_ivars_ = InterfaceObjectIO._excluded_out_ivars_ | {'TotalPurchaseFee'}

@component.adapter(store_interfaces.IPurchaseAttempt)
@interface.implementer(ext_interfaces.IExternalObjectDecorator)
class PurchaseAttemptDecorator(object):

	__metaclass__ = SingletonDecorator

	def decorateExternalObject(self, original, external):
		if store_interfaces.IInvitationPurchaseAttempt.providedBy(original):
			code = invitations.get_invitation_code(original)
			external['InvitationCode'] = code
			external['RemainingInvitations'] = original.tokens

@component.adapter(store_interfaces.IPurchasable)
@interface.implementer(ext_interfaces.IExternalObjectDecorator)
class PurchasableDecorator(object):

	__metaclass__ = SingletonDecorator

	def set_links(self, username, original, external):
		if original.Amount:
			_links = external.setdefault(LINKS, [])
			# insert history link
			if purchase_history.has_history_by_item(username, original.NTIID):
				history_path = DS_STORE_PATH + 'get_purchase_history?purchasableID=%s'
				history_href = history_path % urllib.quote(original.NTIID)
				link = Link(history_href, rel="history")
				interface.alsoProvides(link, ILocation)
				_links.append(link)

			# insert price link
			price_href = DS_STORE_PATH + 'price_purchasable'
			link = Link(price_href, rel="price")
			link.method = 'Post'
			interface.alsoProvides(link, ILocation)
			_links.append(link)
		
	def add_library_details(self, original, external):
		library = component.queryUtility(lib_interfaces.IContentPackageLibrary)
		unit = library.get(original.NTIID) if library else None
		if not original.Title:
			external['Title'] = unit.title if unit else u''
		if not original.Description:
			external['Description'] = unit.title if unit else u''

	def add_activation(self, username, original, external):
		activated = purchase_history.is_item_activated(username, original.NTIID)
		external['Activated'] = activated

	def decorateExternalObject(self, original, external):
		username = authenticated_userid(get_current_request())
		if username:
			self.add_activation(username, original, external)
			self.set_links(username, original, external)
		self.add_library_details(original, external)

@component.adapter(store_interfaces.IPricedItem)
@interface.implementer(ext_interfaces.IExternalObjectDecorator)
class PricedItemDecorator(object):

	__metaclass__ = SingletonDecorator

	def decorateExternalObject(self, original, external):
		non_dist_price = external.get('NonDiscountedPrice', None)
		if 'NonDiscountedPrice' in external and non_dist_price is None:
			del external['NonDiscountedPrice']
		external['Provider'] = original.Provider
		external['Amount'] = original.Amount
		external['Currency'] = original.Currency

@component.adapter(store_interfaces.ICourse)
@interface.implementer(ext_interfaces.IExternalObjectDecorator)
class CourseDecorator(PurchasableDecorator):

	def set_links(self, username, original, external):
		if original.Amount is None:
			_links = external.setdefault(LINKS, [])
			if not purchase_history.has_history_by_item(username, original.NTIID):
				erroll_path = DS_STORE_PATH + 'erroll_course'
				link = Link(erroll_path, rel="erroll")
			else:
				unerroll_path = DS_STORE_PATH + 'unerroll_course'
				link = Link(unerroll_path, rel="erroll")

			link.method = 'Post'
			interface.alsoProvides(link, ILocation)
			_links.append(link)
		else:
			super(CourseDecorator, self).set_links(username, original, external)
