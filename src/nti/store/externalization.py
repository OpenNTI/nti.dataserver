# -*- coding: utf-8 -*-
"""
Store externalization

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from zope import interface
from zope import component

from pyramid.security import authenticated_userid
from pyramid.threadlocal import get_current_request

from nti.externalization import interfaces as ext_interfaces
from nti.externalization.singleton import SingletonDecorator
from nti.externalization.datastructures import InterfaceObjectIO

from nti.contentlibrary import interfaces as lib_interfaces

from . import purchase_history
from . import interfaces as store_interfaces

@interface.implementer(ext_interfaces.IInternalObjectIO)
@component.adapter(store_interfaces.IPurchaseAttempt)
class PurchaseAttemptExternal(InterfaceObjectIO):
	_ext_iface_upper_bound = store_interfaces.IPurchaseAttempt

@interface.implementer(ext_interfaces.IInternalObjectIO)
@component.adapter(store_interfaces.IPurchasable)
class PurchasableExternal(InterfaceObjectIO):
	_ext_iface_upper_bound = store_interfaces.IPurchasable

@component.adapter(store_interfaces.IPurchasable)
@interface.implementer(ext_interfaces.IExternalObjectDecorator)
class PurchasableDecorator(object):

	__metaclass__ = SingletonDecorator

	def decorateExternalObject(self, original, external):
		username = authenticated_userid(get_current_request())
		if username:
			purchased = purchase_history.is_item_purchased(username, original.NTIID)
			external['Purchased'] = purchased

		library = component.queryUtility(lib_interfaces.IContentPackageLibrary)
		unit = library.get(original.NTIID) if library else None
		if not original.Title:
			external['Title'] = unit.title if unit else u''
		if not original.Description:
			external['Description'] = unit.title if unit else u''
