# -*- coding: utf-8 -*-
"""
Defines purchase attempt object.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import time
import functools
from datetime import datetime

from zope import interface
from zope.container import contained as zcontained
from zope.annotation import interfaces as an_interfaces
from zope.schema.fieldproperty import FieldPropertyStoredThroughField as FP

from nti.dataserver.datastructures import ModDateTrackingObject

from nti.externalization.oids import to_external_ntiid_oid

from nti.utils.schema import SchemaConfigured
from nti.zodb.persistentproperty import PersistentPropertyHolder

from . import to_frozenset
from . import interfaces as store_interfaces

@functools.total_ordering
@interface.implementer(store_interfaces.IPurchaseAttempt)
class BasePurchaseAttempt(ModDateTrackingObject, SchemaConfigured):

	Items = FP(store_interfaces.IPurchaseAttempt['Items'])
	Processor = FP(store_interfaces.IPurchaseAttempt['Processor'])
	State = FP(store_interfaces.IPurchaseAttempt['State'])
	Description = FP(store_interfaces.IPurchaseAttempt['Description'])
	StartTime = FP(store_interfaces.IPurchaseAttempt['StartTime'])
	EndTime = FP(store_interfaces.IPurchaseAttempt['EndTime'])
	Quantity = FP(store_interfaces.IPurchaseAttempt['Quantity'])
	ErrorCode = FP(store_interfaces.IPurchaseAttempt['ErrorCode'])
	ErrorMessage = FP(store_interfaces.IPurchaseAttempt['ErrorMessage'])
	Synced = FP(store_interfaces.IPurchaseAttempt['Synced'])

	def __str__(self):
		return "%s,%s" % (self.Items, self.State)

	def __repr__(self):
		d = datetime.fromtimestamp(self.StartTime)
		return "%s(%s,%s,%s)" % (self.__class__, self.Processor, d, self.Items)

	def __eq__(self, other):
		try:
			return self is other or (self.Items == other.Items
									 and self.StartTime == other.StartTime
									 and self.Processor == other.Processor
									 and self.Quantity == other.Quantity)
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
		xhash ^= hash(self.Processor)
		xhash ^= hash(self.StartTime)
		xhash ^= hash(self.Items)
		xhash ^= hash(self.Quantity)
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

@interface.implementer(an_interfaces.IAttributeAnnotatable)
class PurchaseAttempt(BasePurchaseAttempt, zcontained.Contained, PersistentPropertyHolder):

	@property
	def id(self):
		return unicode(to_external_ntiid_oid(self))

	@property
	def creator(self):
		result = getattr(self.__parent__, 'user', None)
		return result

def create_base_purchase_attempt(purchase):
	result = BasePurchaseAttempt(Items=purchase.Items, Processor=purchase.Processor, Description=purchase.Description,
								 State=purchase.State, StartTime=purchase.StartTime, EndTime=purchase.EndTime,
								 Quantity=purchase.Quantity, ErrorCode=purchase.ErrorCode,
								 ErrorMessage=purchase.ErrorMessage, Synced=purchase.Synced)
	return result

def create_purchase_attempt(items, processor, quantity=None, state=None, description=None, start_time=None):
	items = to_frozenset(items)
	start_time = start_time if start_time else time.time()
	state = state or store_interfaces.PA_STATE_UNKNOWN
	result = PurchaseAttempt(Items=items, Processor=processor, Description=description,
							 State=state, StartTime=float(start_time), Quantity=quantity)
	return result
