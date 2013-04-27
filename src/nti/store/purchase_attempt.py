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
from nti.utils.schema import createDirectFieldProperties

from nti.zodb import minmax
from nti.zodb.persistentproperty import PersistentPropertyHolder

from . import purchase_order
from .utils import MetaStoreObject
from . import interfaces as store_interfaces

@functools.total_ordering
@interface.implementer(store_interfaces.IPurchaseAttempt, an_interfaces.IAttributeAnnotatable, zmime_interfaces.IContentTypeAware)
class PurchaseAttempt(ModDateTrackingObject, SchemaConfigured, zcontained.Contained, PersistentPropertyHolder):

	__external_class_name__ = "PurchaseAttempt"
	__metaclass__ = MetaStoreObject


	# create all interface fields
	createDirectFieldProperties(store_interfaces.IPurchaseAttempt)

	@property
	def Items(self):
		return self.Order.NTIIDs

	@property
	def Quantity(self):
		return self.Order.Quantity

	@property
	def id(self):
		return unicode(to_external_ntiid_oid(self))

	@property
	def creator(self):
		result = getattr(self.__parent__, 'user', None)
		return result

	def __str__(self):
		return "%s,%s" % (self.Items, self.State)

	def __repr__(self):
		d = datetime.fromtimestamp(self.StartTime)
		return "%s(%s,%s,%s,%s)" % (self.__class__.__name__, self.Items, self.State, self.Processor, d)

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

@interface.implementer(store_interfaces.IInvitationPurchaseAttempt)
class InvitationPurchaseAttempt(PurchaseAttempt):

	def __init__(self, *args, **kwargs):
		super(PurchaseAttempt, self).__init__(*args, **kwargs)
		self._consumers = BTrees.OOBTree.OOBTree()
		self._tokens = minmax.NumericMinimum(self.Quantity)

	def register(self, user, linked_purchase_id=None):
		user = getattr(user, "username", user)
		if user and not user in self._consumers:
			self._consumers[user] = linked_purchase_id
			return True
		return False

	@property
	def tokens(self):
		return self._tokens.value

	def consume_token(self):
		if self._tokens.value > 0:
			self._tokens -= 1
			return True
		return False

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
	cls = PurchaseAttempt if not order.Quantity else InvitationPurchaseAttempt
	result = cls(Order=order, Processor=processor, Description=description,
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

