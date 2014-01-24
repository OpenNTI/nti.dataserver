#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Stripe decorators

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os

from zope import interface
from zope import component
from zope.container.interfaces import ILocation

from pyramid.threadlocal import get_current_request

from nti.dataserver.links import Link

from nti.externalization.singleton import SingletonDecorator
from nti.externalization import interfaces as ext_interfaces
from nti.externalization.externalization import toExternalObject

from . import interfaces as stripe_interfaces
from ...decorators import PricedItemDecorator
from ... import interfaces as store_interfaces

LINKS = ext_interfaces.StandardExternalFields.LINKS

@component.adapter(stripe_interfaces.IStripePricedItem)
@interface.implementer(ext_interfaces.IExternalObjectDecorator)
class StripePricedItemDecorator(PricedItemDecorator):
	pass

@component.adapter(store_interfaces.IPurchasable)
@interface.implementer(ext_interfaces.IExternalObjectDecorator)
class PurchasableDecorator(object):

	__metaclass__ = SingletonDecorator

	def set_links(self, original, external):
		request = get_current_request()
		if original.Amount and request:
			_ds_path = os.path.split(request.current_route_path())[0]
			price_href = _ds_path + '/price_purchasable_with_stripe_coupon'
			link = Link(price_href, rel="price_with_stripe_coupon", method='Post')
			interface.alsoProvides(link, ILocation)
			external.setdefault(LINKS, []).append(link)

	def decorateExternalObject(self, original, external):
		keyname = original.Provider
		result = component.queryUtility(stripe_interfaces.IStripeConnectKey, keyname)
		if result:
			external['StripeConnectKey'] = toExternalObject(result)
		self.set_links(original, external)
