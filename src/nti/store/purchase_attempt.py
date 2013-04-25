# -*- coding: utf-8 -*-
"""
Defines purchase attempt object.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import time
import BTrees
import functools
from datetime import datetime

from zope import interface
from zope.container import contained as zcontained
from zope.annotation import interfaces as an_interfaces
from zope.mimetype import interfaces as zmime_interfaces
from zope.schema.fieldproperty import FieldPropertyStoredThroughField as FP

from nti.dataserver.datastructures import ModDateTrackingObject

from nti.externalization.oids import to_external_ntiid_oid

from nti.utils.schema import SchemaConfigured

from nti.zodb import minmax
from nti.zodb.persistentproperty import PersistentPropertyHolder

from . import purchase_order
from .utils import MetaStoreObject
from . import interfaces as store_interfaces

@functools.total_ordering
@interface.implementer(store_interfaces.IPurchaseAttempt)
class BasePurchaseAttempt(ModDateTrackingObject, SchemaConfigured):

	Order = FP(store_interfaces.IPurchaseAttempt['Order'])
	Processor = FP(store_interfaces.IPurchaseAttempt['Processor'])
	State = FP(store_interfaces.IPurchaseAttempt['State'])
	Description = FP(store_interfaces.IPurchaseAttempt['Description'])
	StartTime = FP(store_interfaces.IPurchaseAttempt['StartTime'])
	EndTime = FP(store_interfaces.IPurchaseAttempt['EndTime'])
	Error = FP(store_interfaces.IPurchaseAttempt['Error'])
	Synced = FP(store_interfaces.IPurchaseAttempt['Synced'])

	@property
	def Items(self):
		return self.Order.NTIIDs

	@property
	def Quantity(self):
		return self.Order.Quantity

	def __str__(self):
		return "%s,%s" % (self.Items, self.State)

	def __repr__(self):
		d = datetime.fromtimestamp(self.StartTime)
		return "%s(%s,%s,%s,%s)" % (self.__class__.__name__, self.Processor, d, self.Items, self.State)

	def __eq__(self, other):
		try:
			return self is other or (self.Order == other.Order
									 and self.StartTime == other.StartTime
									 and self.Processor == other.Processor)
		except AttributeError:
			return NotImplemented

	def __lt__(self, other):
		try:
			return self.StartTime < other.StartTime
		except AttributeError:
			return NotImplemented

	def __gt__(self, other):
		try:
			return self.StartTime > other.StartTime
		except AttributeError:
			return NotImplemented

	def __hash__(self):
		xhash = 47
		xhash ^= hash(self.Order)
		xhash ^= hash(self.Processor)
		xhash ^= hash(self.StartTime)
		return xhash

	def has_failed(self):
		return self.State in (store_interfaces.PA_STATE_FAILED, store_interfaces.PA_STATE_FAILURE, store_interfaces.PA_STATE_CANCELED)

	def has_succeeded(self):
		return self.State == store_interfaces.PA_STATE_SUCCESS

	def is_unknown(self):
		return self.State == store_interfaces.PA_STATE_UNKNOWN

	def is_pending(self):
		return self.State in (store_interfaces.PA_STATE_STARTED, store_interfaces.PA_STATE_PENDING)

	def is_refunded(self):
		return self.State == store_interfaces.PA_STATE_REFUNDED

	def is_disputed(self):
		return self.State == store_interfaces.PA_STATE_DISPUTED

	def is_reserved(self):
		return self.State == store_interfaces.PA_STATE_RESERVED

	def is_canceled(self):
		return self.State == store_interfaces.PA_STATE_CANCELED

	def has_completed(self):
		return not (self.is_pending() or self.is_reserved() or self.is_disputed())

	def is_synced(self):
		return self.Synced

@interface.implementer(an_interfaces.IAttributeAnnotatable, zmime_interfaces.IContentTypeAware)
class PurchaseAttempt(BasePurchaseAttempt, zcontained.Contained, PersistentPropertyHolder):

	__metaclass__ = MetaStoreObject

	_tokens = None
	_consumers = None

	def __init__(self, *args, **kwargs):
		super(PurchaseAttempt, self).__init__(*args, **kwargs)
		if self.Quantity:
			self._consumers = BTrees.OOBTree.OOTreeSet()
			self._tokens = minmax.NumericMinimum(self.Quantity)

	@property
	def id(self):
		return unicode(to_external_ntiid_oid(self))

	@property
	def creator(self):
		result = getattr(self.__parent__, 'user', None)
		return result

	# invitations

	def register(self, user, linked_purchase_id=None):
		if self._consumers is not None:
			user = getattr(user, "username", user)
			if not user in self._consumers and user:
				self._consumers.add(user)
				return True
			else:
				return False
		return True

	@property
	def tokens(self):
		return self._tokens.value if self._tokens is not None else None

	def consume_token(self):
		if self._tokens is not None:
			if self._tokens.value > 0:
				self._tokens -= 1
			else:
				return False
		return True

	def __str__(self):
		return self.id

@interface.implementer(store_interfaces.IRedeemedPurchaseAttempt)
class RedeemedPurchaseAttempt(PurchaseAttempt):
	RedemptionCode = FP(store_interfaces.IRedeemedPurchaseAttempt['RedemptionCode'])
	RedemptionTime = FP(store_interfaces.IRedeemedPurchaseAttempt['RedemptionTime'])

def get_purchasables(purchase):
	return purchase_order.get_purchasables(purchase.Order)

def get_providers(purchase):
	return purchase_order.get_providers(purchase.Order)

def get_currencies(purchase):
	return purchase_order.get_currencies(purchase.Order)

def create_purchase_attempt(order, processor, state=None, description=None, start_time=None):
	state = state or store_interfaces.PA_STATE_UNKNOWN
	start_time = start_time if start_time else time.time()
	result = PurchaseAttempt(Order=order, Processor=processor, Description=description,
							 State=state, StartTime=float(start_time))
	return result

def create_redeemed_purchase_attempt(purchase, redemption_code, redemption_time=None):

	redemption_time = redemption_time if redemption_time else time.time()

	# copy with order quantity none and item quantity to 1
	new_order = purchase.Order.copy()
	new_order.Quantity = None
	purchase_order.replace_quantity(new_order, 1)

	result = RedeemedPurchaseAttempt(Order=new_order, Processor=purchase.Processor, Description=purchase.Description,
							 		 State=purchase.State, StartTime=purchase.StartTime, EndTime=purchase.EndTime,
									 Error=purchase.Error, Synced=purchase.Synced, RedemptionTime=float(redemption_time),
									 RedemptionCode=unicode(redemption_code))
	return result
