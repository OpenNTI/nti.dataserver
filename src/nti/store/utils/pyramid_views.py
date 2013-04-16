# -*- coding: utf-8 -*-
"""
Store pyramid views.

$Id: pyramid_views.py 18274 2013-04-16 16:37:36Z carlos.sanchez $
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from pyramid import httpexceptions as hexc

from . import is_valid_amount
from . import is_valid_pve_int
from .. import purchasable_store

class PricePurchasableView(object):

	def __init__(self, request):
		self.request = request

	def price_purchasable(self, required=False):
		request = self.request

		params = request.params
		purchasableID = params.get('purchasableID', '+++invalid+++' if required else None)
		purchasable = purchasable_store.get_purchasable(purchasableID) if purchasableID else None
		if purchasableID and not purchasable:
			raise hexc.HTTPBadRequest(detail='invalid purchasable')
		elif purchasable is not None:
			amount = purchasable.Amount
		else:
			amount = params.get('amount', None)
			if amount is not None and not is_valid_amount(amount):
				raise hexc.HTTPBadRequest(detail='invalid amount')

		# check quantity
		quantity = params.get('quantity', 1)
		if not is_valid_pve_int(quantity):
			raise hexc.HTTPBadRequest(detail='invalid quantity')

		# calculate new amount
		new_amount = amount * int(quantity) if amount else None

		return (purchasable, quantity, new_amount)

	def __call__(self):
		_, _, new_amount = self.price_purchasable(required=True)
		if new_amount is None:
			raise hexc.HTTPBadRequest(detail='invalid amount')
		return {'NewAmount':new_amount}
