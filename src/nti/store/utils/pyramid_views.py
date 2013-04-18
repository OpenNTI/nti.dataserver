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

from . import is_valid_amount
from . import is_valid_pve_int
from .. import purchasable_store
from . import CaseInsensitiveDict

class PricePurchasableView(object):

	invalid_id = '+++etc+++invalid+++'

	def __init__(self, request):
		self.request = request

	def readInput(self):
		request = self.request
		values = simplejson.loads(unicode(request.body, request.charset))
		return CaseInsensitiveDict(**values)

	def price_purchasable(self, required=False):
		values = self.readInput()
		purchasableID = values.get('purchasableID', self.invalid_id if required else None)
		purchasable = purchasable_store.get_purchasable(purchasableID) if purchasableID else None

		if purchasableID and not purchasable:
			raise hexc.HTTPBadRequest(detail='invalid purchasable')
		elif purchasable is not None:
			amount = purchasable.Amount
		else:
			amount = values.get('amount', None)

		if amount is None or not is_valid_amount(amount):
			raise hexc.HTTPBadRequest(detail='invalid amount')

		# check quantity
		quantity = values.get('quantity', 1)
		if not is_valid_pve_int(quantity):
			raise hexc.HTTPBadRequest(detail='invalid quantity')

		# calculate new amount
		new_amount = float(amount) * int(quantity)

		result = CaseInsensitiveDict(**values)
		result['Amount'] = float(amount)
		result['NewAmount'] = new_amount
		result['Quantity'] = int(quantity)
		result['Purchasable'] = purchasable
		return result

	def __call__(self):
		result = self.price_purchasable(required=True)
		amount = result.get('Amount')
		new_amount = result.get('NewAmount')
		return LocatedExternalDict({'NewAmount':new_amount, 'Amount':amount})
