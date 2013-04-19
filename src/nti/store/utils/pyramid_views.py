# -*- coding: utf-8 -*-
"""
Store pyramid views.

$Id: pyramid_views.py 18274 2013-04-16 16:37:36Z carlos.sanchez $
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import simplejson

from pyramid import httpexceptions as hexc

from nti.externalization.datastructures import LocatedExternalDict
from nti.externalization.externalization import to_external_object

from . import is_valid_pve_int
from .. import purchasable_store
from . import CaseInsensitiveDict
from .. import priced_purchasable

class PricePurchasableView(object):

	def __init__(self, request):
		self.request = request

	def readInput(self):
		request = self.request
		values = simplejson.loads(unicode(request.body, request.charset))
		return CaseInsensitiveDict(**values)

	def price_purchasable(self, values=None):
		values = values or self.readInput()
		purchasable_id = values.get('purchasableID', None)
		purchasable = purchasable_store.get_purchasable(purchasable_id)
		if not purchasable:
			raise hexc.HTTPBadRequest(detail='invalid purchasable (%s)' % purchasable_id)

		# check quantity
		quantity = values.get('quantity', 1)
		if not is_valid_pve_int(quantity):
			raise hexc.HTTPBadRequest(detail='invalid quantity')
		quantity = int(quantity)

		# calculate new amount
		amount = purchasable.Amount
		new_amount = amount * quantity

		fee_amount = 0
		fee = purchasable.Fee
		if fee is not None:
			pct = fee / 100.0 if fee >= 1 else fee
			fee_amount = new_amount * pct

		result = priced_purchasable.create_priced_purchasable(purchasable_id, new_amount, fee_amount)
		return result, quantity

	def __call__(self):
		priced, quantity = self._price_purchasable()
		ext = to_external_object(priced)
		result = LocatedExternalDict(**ext)
		result['Quantity'] = [quantity]
		return result
