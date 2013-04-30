# -*- coding: utf-8 -*-
"""
Stripe utilities.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"


import six
import time
import simplejson as json

from nti.store import payment_charge
from nti.store import NTIStoreException
from . import interfaces as stripe_interfaces
from nti.store import interfaces as store_interfaces

def makenone(s, default=None):
	if isinstance(s, six.string_types):
		s = default if s == 'None' else unicode(s)
	return s

def encode_charge_description(purchase_id, username, customer_id):
	"""
	proceduce a json object for a stripe charge description
	"""
	data = {'PurchaseID': purchase_id, 'Username':username, 'CustomerID': customer_id}
	result = json.dumps(data)
	return result

def decode_charge_description(s):
	"""
	decode a stripe charge description
	"""
	try:
		result = json.loads(s)
	except (TypeError, ValueError):
		result = {}
	return result

def create_user_address(charge):
	"""
	creates a payment_charge.UserAddress from a stripe charge
	"""
	card = getattr(charge, 'card', None)
	if card is not None:
		address = payment_charge.UserAddress.create(makenone(card.address_line1),
 													makenone(card.address_line2),
 													makenone(card.address_city),
 													makenone(card.address_state),
 													makenone(card.address_zip),
 													makenone(card.address_country))
		return address
	return payment_charge.UserAddress()

def get_card_info(charge):
	"""
	return card info from a stripe charge
	"""
	card = getattr(charge, 'card', None)
	name = getattr(card, 'name', None)
	last4 = getattr(card, 'last4', None)
	last4 = int(last4) if last4 is not None else None
	return (last4, name)

def create_payment_charge(charge):
	"""
	creates a payment_charge.PaymentCharge from a stripe charge
	"""
	amount = charge.amount / 100.0
	currency = charge.currency.upper()
	last4, name = get_card_info(charge)
	address = create_user_address(charge)
	created = float(charge.created or time.time())
	result = payment_charge.PaymentCharge(Amount=amount, Currency=currency, Created=created,
										  CardLast4=last4, Address=address, Name=name)
	return result

def adapt_to_error(e):
	"""
	adapts an exception to a IStripePurchaseError
	"""
	result = store_interfaces.IPurchaseError(e, None) or stripe_interfaces.IStripePurchaseError(e, None)
	if result is None and isinstance(e, Exception):
		result = store_interfaces.IPurchaseError(NTIStoreException(e.args), None)
	return result
