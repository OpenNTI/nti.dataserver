#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
Store decorators

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import urllib

from zope import interface
from zope import component
from zope.container.interfaces import ILocation

from pyramid.threadlocal import get_current_request

from nti.dataserver.links import Link

from nti.externalization import interfaces as ext_interfaces
from nti.externalization.singleton import SingletonDecorator

from nti.contentlibrary import interfaces as lib_interfaces

from . import invitations
from . import purchase_history
from . import interfaces as store_interfaces

LINKS = ext_interfaces.StandardExternalFields.LINKS

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

	def set_links(self, request, username, original, external):
		if original.Amount:
			_ds_path = '/dataserver2/store/'
			_links = external.setdefault(LINKS, [])

			# insert history link
			if purchase_history.has_history_by_item(username, original.NTIID):
				history_path = _ds_path + 'get_purchase_history?purchasableID=%s'
				history_href = history_path % urllib.quote(original.NTIID)
				link = Link(history_href, rel="history")
				interface.alsoProvides(link, ILocation)
				_links.append(link)

			# insert price link
			price_href = _ds_path + 'price_purchasable'
			link = Link(price_href, rel="price", method='Post')
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
		# XXX: FIXME: Hack for some borked objects, hopefully only in alpha database
		# See purchase_history for more details
		if activated and store_interfaces.ICourse.providedBy(original):
			# We can easily get out of sync here if the purchase object
			# itself has been removed/lost. This will result in logging a
			# warning if so.
			from . import enrollment
			activated = enrollment.is_enrolled( username, original.NTIID )
		external['Activated'] = activated

	def decorateExternalObject(self, original, external):
		request = get_current_request()
		username = request.authenticated_userid if request else None
		if username:
			self.add_activation(username, original, external)
			self.set_links(request, username, original, external)
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

	def set_links(self, request, username, original, external):
		if original.Amount is not None:
			super(CourseDecorator, self).set_links(request, username, original, external)
		else:
			_ds_path = '/dataserver2/store/'
			if not purchase_history.has_history_by_item(username, original.NTIID):
				erroll_path = _ds_path + 'enroll_course'
				link = Link(erroll_path, rel="enroll", method='Post')
			else:
				unerroll_path = _ds_path + 'unenroll_course'
				link = Link(unerroll_path, rel="unenroll", method='Post')
			interface.alsoProvides(link, ILocation)
			external.setdefault(LINKS, []).append(link)
