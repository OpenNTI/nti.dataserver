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

from pyramid.security import authenticated_userid
from pyramid.threadlocal import get_current_request

from nti.dataserver.links import Link

from nti.externalization import interfaces as ext_interfaces
from nti.externalization.singleton import SingletonDecorator
from nti.externalization.datastructures import InterfaceObjectIO
from nti.externalization.externalization import toExternalObject
from nti.externalization.datastructures import LocatedExternalDict

from nti.contentlibrary import interfaces as lib_interfaces

from . import invitations
from . import purchase_history
from . import interfaces as store_interfaces

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
@component.adapter(store_interfaces.IRedeemedPurchaseAttempt)
class RedeemedPurchaseAttemptExternal(InterfaceObjectIO):
	_ext_iface_upper_bound = store_interfaces.IRedeemedPurchaseAttempt

@component.adapter(store_interfaces.IPurchasable)
@interface.implementer(ext_interfaces.IExternalObjectDecorator)
class PurchaseAttemptDecorator(object):

	__metaclass__ = SingletonDecorator

	def decorateExternalObject(self, original, external):
		if original.Quantity:
			code = invitations.get_invitation_code(original)
			external['InvitationCode'] = code
			external['RemainingnInvitations'] = original.tokens

@interface.implementer(ext_interfaces.IInternalObjectIO)
@component.adapter(store_interfaces.IPurchasable)
class PurchasableExternal(InterfaceObjectIO):
	_ext_iface_upper_bound = store_interfaces.IPurchasable

@component.adapter(store_interfaces.IPurchasable)
@interface.implementer(ext_interfaces.IExternalObjectDecorator)
class PurchasableDecorator(object):

	__metaclass__ = SingletonDecorator

	def set_links(self, username, original, external):
		request = get_current_request()
		if request is None: return

		# insert history link
		if purchase_history.has_history_by_item(username, original.NTIID):
			link_hist_href = "/dataserver2/store/get_purchase_history?purchasableID=" + urllib.quote(original.NTIID)
			link_hist = Link(link_hist_href, rel="history")
			external.setdefault('Links', []).append(link_hist)

	def decorateExternalObject(self, original, external):
		# check if item has been purchased
		username = authenticated_userid(get_current_request())
		if username:
			activated = purchase_history.is_item_activated(username, original.NTIID)
			external['Activated'] = activated
			self.set_links(username, original, external)

		# fill details from library
		library = component.queryUtility(lib_interfaces.IContentPackageLibrary)
		unit = library.get(original.NTIID) if library else None
		if not original.Title:
			external['Title'] = unit.title if unit else u''
		if not original.Description:
			external['Description'] = unit.title if unit else u''

@interface.implementer(ext_interfaces.IInternalObjectIO)
@component.adapter(store_interfaces.IPriceable)
class PriceableExternal(InterfaceObjectIO):
	_ext_iface_upper_bound = store_interfaces.IPriceable

@interface.implementer(ext_interfaces.IInternalObjectIO)
@component.adapter(store_interfaces.IPricedItem)
class PricedItemExternal(InterfaceObjectIO):
	_ext_iface_upper_bound = store_interfaces.IPricedItem
	_excluded_out_ivars_ = InterfaceObjectIO._excluded_out_ivars_ | {'PurchaseFee'}

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

@component.adapter(store_interfaces.IPricedItems)
@interface.implementer(ext_interfaces.IExternalObject)
class PricedItemsExternalizer(object):

	def __init__(self, results):
		self.results = results

	def toExternalObject(self):
		external = LocatedExternalDict()
		external.lastModified = 0
		external.mimeType = self.results.mimeType

		items = external['Items'] = []
		for priced in self.results.PricedList:
			ext = toExternalObject(priced)
			items.append(ext)

		external['TotalPurchasePrice'] = self.results.TotalPurchasePrice
		if self.results.TotalNonDiscountedPrice:
			external['TotalNonDiscountedPrice'] = self.results.TotalNonDiscountedPrice
		return external
