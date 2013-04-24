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
import simplejson
import dateutil.parser

from pyramid import httpexceptions as hexc

from zope import component

from pyramid.security import authenticated_userid

from nti.dataserver import interfaces as nti_interfaces

from nti.externalization.datastructures import LocatedExternalDict

from . import priceable
from . import purchasable
from . import invitations
from . import purchase_history
from . import InvalidPurchasable
from . import interfaces as store_interfaces
from .payments import pyramid_views as payment_pyramid
from .utils import is_valid_pve_int, CaseInsensitiveDict, raise_field_error, is_valid_timestamp

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
		if is_valid_timestamp(t):
			result = float(t)
		elif isinstance(t, six.string_types):
			result = time.mktime(dateutil.parser(t).timetuple())
		return result if isinstance(t, numbers.Number) else None

	def __call__(self):
		request = self.request
		username = authenticated_userid(request)
		purchasable_id = request.params.get('purchasableID', None)
		if not purchasable_id:
			start_time = self._convert(request.params.get('startTime', None))
			end_time = self._convert(request.params.get('endTime', None))
			purchases = purchase_history.get_purchase_history(username, start_time, end_time)
		else:
			purchases = purchase_history.get_purchase_history_by_item(purchasable_id)
		result = LocatedExternalDict({'Items': purchases, 'Last Modified':self._last_modified(purchases)})
		return result

class GetPurchaseAttemptView(object):

	def __init__(self, request):
		self.request = request

	def __call__(self):
		request = self.request
		username = authenticated_userid(request)
		purchase_id = request.params.get('purchaseID')
		if not purchase_id:
			raise_field_error(request, "purchaseID", "Failed to provide a purchase attempt ID")

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
		purchasables = purchasable.get_all_purchasables()
		result = LocatedExternalDict({'Items': purchasables, 'Last Modified':0})
		return result

class _PostView(object):

	def __init__(self, request):
		self.request = request

	def readInput(self):
		request = self.request
		values = simplejson.loads(unicode(request.body, request.charset))
		return CaseInsensitiveDict(**values)

class RedeemPurchaseCodeView(_PostView):

	def __call__(self):
		request = self.request
		values = self.readInput()
		purchasable_id = values.get('purchasableID')
		if not purchasable_id:
			raise_field_error(request, "purchasableID", "Failed to provide a purchasable ID")

		invitation_code = values.get('invitationCode', values.get('invitation_code'))
		if not invitation_code:
			raise_field_error(request, "invitation_code", "Failed to provide a invitation code")

		purchase = invitations.get_purchase_by_code(invitation_code)
		if purchase is None or not store_interfaces.IPurchaseAttempt.provideBy(purchase):
			raise hexc.HTTPNotFound(detail='Purchase attempt not found')

		if purchase.Quantity is None:
			raise hexc.HTTPUnprocessableEntity(detail='Not redeemable purchase')

		if purchasable_id not in purchase.Items:
			raise_field_error(request, "invitation_code", "The invitation code is not for this purchasable")

		username = authenticated_userid(request)
		invite = invitations.create_store_purchase_invitation(purchase, invitation_code)
		invite.accept(username)

		return hexc.HTTPNoContent()

class PricePurchasableView(_PostView):

	def price(self, purchasable_id, quantity):
		pricer = component.getUtility(store_interfaces.IPurchasablePricer)
		source = priceable.create_priceable(purchasable_id, quantity)
		result = pricer.price(source)
		return result

	def price_purchasable(self, values=None):
		values = values or self.readInput()
		purchasable_id = values.get('purchasableID', u'')

		# check quantity
		quantity = values.get('quantity', 1)
		if not is_valid_pve_int(quantity):
			raise_field_error(self.request, 'quantity', 'invalid quantity')
		quantity = int(quantity)

		try:
			result = self.price(purchasable_id, quantity)
			return result
		except InvalidPurchasable:
			raise_field_error(self.request, 'purchasableID', 'purchasable not found')

	def __call__(self):
		result = self.price_purchasable()
		return result

# aliases

StripePaymentView = payment_pyramid.StripePaymentView
CreateStripeTokenView = payment_pyramid.CreateStripeTokenView
GetStripeConnectKeyView = payment_pyramid.GetStripeConnectKeyView
PricePurchasableWithStripeCouponView = payment_pyramid.PricePurchasableWithStripeCouponView
