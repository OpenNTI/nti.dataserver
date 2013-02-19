# -*- coding: utf-8 -*-
"""
Defines purchase attempt object.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

import re
import six
import time
import functools
from datetime import datetime

import persistent
from zope import interface
from zope.container import contained as zcontained
from zope.annotation import interfaces as an_interfaces

from nti.dataserver.datastructures import ModDateTrackingObject

from nti.externalization.oids import to_external_ntiid_oid

from nti.utils.property import alias

from . import interfaces as store_interfaces

def _from_unicode(value):
	result = value.split(',')
	result = re.findall("[^\s]+", value) if len(result)<=1 else result
	return result

def _to_collection(items=None, factory=list):
	result = None
	if not items:
		result = factory()
	elif isinstance(items, factory):
		result = items
	elif isinstance(items, six.string_types):
		result = factory(_from_unicode(items))
	else:
		result = factory(items)
	return result

def to_list(items=None):
	return _to_collection(items, list)

def to_frozenset(items=None):
	return _to_collection(items, frozenset)

_marker_frozenset = frozenset()

@functools.total_ordering
@interface.implementer(store_interfaces.IPurchaseAttempt, an_interfaces.IAttributeAnnotatable)
class PurchaseAttempt(zcontained.Contained, ModDateTrackingObject, persistent.Persistent):

	Synced = False
	EndTime = None
	ErrorCode = None
	Description = None
	ErrorMessage = None
	OnBehalfOf = _marker_frozenset

	def __init__(self, items, processor, state, description=None, start_time=None, end_time=None,
				 on_behalf_of=None, error_code=None, error_message=None, synced=False):

		self.State = state
		self.Processor = processor
		self.Items = to_frozenset(items)
		self.StartTime = start_time if start_time else time.time()
		if on_behalf_of:
			self.OnBehalfOf = to_frozenset(on_behalf_of)
		if end_time is not None:
			self.EndTime = end_time
		if error_code:
			self.ErrorCode = error_code
		if error_message:
			self.ErorrMessage = error_message
		if description:
			self.Description = description
		if synced == True:
			self.Synced = True

	state = alias('State')
	items = alias('Items')
	synced = alias('Synced')
	processor = alias('Processor')
	start_time = alias('StartTime')
	on_behalf_of = alias('OnBehalfOf')
	description = alias('Description')

	@property
	def id(self):
		return unicode(to_external_ntiid_oid(self))

	@property
	def creator(self):
		result = getattr(self.__parent__, 'user', None)
		return result

	def __str__( self ):
		return "%s,%s" % (self.items, self.state)

	def __repr__( self ):
		d = datetime.fromtimestamp(self.start_time)
		return "%s(%s,%s,%s)" % (self.__class__, self.processor, d, self.items)

	def __eq__(self, other):
		return self is other or (isinstance(other, PurchaseAttempt)
								 and self.items == other.items
								 and self.start_time == other.start_time
								 and self.processor == other.processor
								 and self.on_behalf_of == other.on_behalf_of)

	def __lt__(self, other):
		try:
			return self.start_time < other.start_time
		except AttributeError:
			return NotImplemented

	def __gt__(self,other):
		try:
			return self.start_time > other.start_time
		except AttributeError:
			return NotImplemented

	def __hash__( self ):
		xhash = 47
		xhash ^= hash(self.Processor)
		xhash ^= hash(self.StartTime)
		xhash ^= hash(self.Items)
		xhash ^= hash(self.OnBehalfOf)
		return xhash

	def actors(self):
		result = self.on_behalf_of.union(set([self.creator.username]))
		return result

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

def create_purchase_attempt(items, processor, on_behalf_of=None, state=None, description=None, start_time=None):
	items = to_frozenset(items)
	state = state or store_interfaces.PA_STATE_UNKNOWN
	return PurchaseAttempt(	items=items, processor=processor, description=description,
							state=state, start_time=start_time, on_behalf_of=on_behalf_of)
