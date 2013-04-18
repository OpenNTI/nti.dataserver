# -*- coding: utf-8 -*-
"""
Store pyramid views.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import six
import time
import gevent
import numbers
import dateutil.parser

from pyramid import httpexceptions as hexc

from zope import component

from pyramid.security import authenticated_userid

from nti.dataserver import interfaces as nti_interfaces

from nti.externalization.datastructures import LocatedExternalDict

from . import purchase_history
from . import purchasable_store
from . import interfaces as store_interfaces
from .utils import pyramid_views as util_pyramid
from .payments import pyramid_views as payment_pyramid

class _PurchaseAttemptView(object):

	def __init__(self, request):
		self.request = request

	def _last_modified(self, purchases):
		result = 0
		for pa in purchases or ():
			result = max(result, getattr(pa, "lastModified", 0))
		return result

class GetPendingPurchasesView(_PurchaseAttemptView):

	def __init__(self, request):
		self.request = request

	def __call__(self):
		request = self.request
		username = authenticated_userid(request)
		purchases = purchase_history.get_pending_purchases(username)
		result = LocatedExternalDict({'Items': purchases, 'Last Modified':self._last_modified(purchases)})
		return result

class GetPurchaseHistoryView(_PurchaseAttemptView):

	def __init__(self, request):
		self.request = request

	def _convert(self, t):
		result = t
		if isinstance(t, six.string_types):
			result = time.mktime(dateutil.parser(t).timetuple())
		return result if isinstance(t, numbers.Number) else None

	def __call__(self):
		request = self.request
		username = authenticated_userid(request)
		start_time = self._convert(request.params.get('startTime', None))
		end_time = self._convert(request.params.get('endTime', None))
		purchases = purchase_history.get_purchase_history(username, start_time, end_time)
		result = LocatedExternalDict({'Items': purchases, 'Last Modified':self._last_modified(purchases)})
		return result

class GetPurchaseAttemptView(object):

	def __init__(self, request):
		self.request = request

	def __call__(self):
		request = self.request
		username = authenticated_userid(request)
		purchase_id = request.params.get('purchaseID', request.params.get('OID', None))
		if not purchase_id:
			raise hexc.HTTPBadRequest(detail="Failed to provide a purchase attempt ID")
		purchase = purchase_history.get_purchase_attempt(purchase_id, username)
		if purchase is None:
			raise hexc.HTTPNotFound(detail='Purchase attempt not found')
		elif purchase.is_pending():
			start_time = purchase.StartTime
			# more than 90 secs try to sync
			if time.time() - start_time >= 90 and not purchase.is_synced():

				def sync_purchase():
					manager = component.getUtility(store_interfaces.IPaymentProcessor, name=purchase.Processor)
					manager.sync_purchase(purchase_id=purchase_id, username=username)

				def process_sync():
					component.getUtility(nti_interfaces.IDataserverTransactionRunner)(sync_purchase)

				gevent.spawn(process_sync)

		result = LocatedExternalDict({'Items':[purchase], 'Last Modified':purchase.lastModified})
		return result

class GetPurchasablesView(object):

	def __init__(self, request):
		self.request = request

	def __call__(self):
		purchasables = purchasable_store.get_all_purchasables()
		result = LocatedExternalDict({'Items': purchasables, 'Last Modified':0})
		return result

# alias

StripePaymentView = payment_pyramid.StripePaymentView
PricePurchasableView = util_pyramid.PricePurchasableView
CreateStripeTokenView = payment_pyramid.CreateStripeTokenView
GetStripeConnectKeyView = payment_pyramid.GetStripeConnectKeyView
PricePurchasableWithStripeCouponView = payment_pyramid.PricePurchasableWithStripeCouponView
