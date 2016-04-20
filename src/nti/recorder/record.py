#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from functools import total_ordering

from zope import interface

from zope.container.contained import Contained

from zope.deprecation import deprecated

from zope.mimetype.interfaces import IContentTypeAware

from persistent import Persistent

from nti.common.property import alias

from nti.dublincore.datastructures import PersistentCreatedModDateTrackingObject

from nti.externalization.representation import WithRepr

from nti.recorder.interfaces import TRX_TYPE_UPDATE
from nti.recorder.interfaces import TRX_RECORD_HISTORY_KEY

from nti.recorder.interfaces import ITransactionRecord
from nti.recorder.interfaces import ITransactionRecordHistory

from nti.schema.field import SchemaConfigured
from nti.schema.fieldproperty import createDirectFieldProperties

from nti.schema.schema import EqHash

@WithRepr
@total_ordering
@EqHash('principal', 'createdTime', 'tid')
@interface.implementer(ITransactionRecord, IContentTypeAware)
class TransactionRecord(PersistentCreatedModDateTrackingObject,
			 			SchemaConfigured,
			 			Contained):

	createDirectFieldProperties(ITransactionRecord)

	type = TRX_TYPE_UPDATE
	serial = alias('tid')
	username = alias('principal')

	parameters = {} # IContentTypeAware

	def __init__(self, *args, **kwargs):
		SchemaConfigured.__init__(self, *args, **kwargs)
		PersistentCreatedModDateTrackingObject.__init__(self)

	@property
	def key(self):
		return "(%s,%s,%s)" % (self.createdTime, self.principal, self.tid)

	def __lt__(self, other):
		try:
			return (self.principal, self.createdTime) < (self.principal, self.createdTime)
		except AttributeError:  # pragma: no cover
			return NotImplemented

	def __gt__(self, other):
		try:
			return (self.principal, self.createdTime) > (self.principal, self.createdTime)
		except AttributeError:  # pragma: no cover
			return NotImplemented

deprecated('TransactionRecordHistory', 'No longer used')
class TransactionRecordHistory(Contained, Persistent):
	_records = ()

def has_transactions(obj):
	result = False
	try:
		annotations = obj.__annotations__
		history = annotations.get(TRX_RECORD_HISTORY_KEY, None)
		result = bool(history)
	except AttributeError:
		pass
	return result
hasTransactions = has_transactions

def get_transactions(obj, sort=False, descending=True):
	result = []
	try:
		annotations = obj.__annotations__
		history = annotations.get(TRX_RECORD_HISTORY_KEY, None)
		if history:
			result.extend(history.records())
		if sort:
			result.sort(key=lambda t: t.createdTime, reverse=descending)
	except AttributeError:
		pass
	return tuple(result)
getTransactions = get_transactions

def remove_transaction_history(obj):
	try:
		annotations = obj.__annotations__
		history = annotations.pop(TRX_RECORD_HISTORY_KEY, None)
		if history:
			return history.clear()
	except AttributeError:
		pass
	return 0
removeTransactionHistory = remove_history = remove_transaction_history

def append_records(target, records=()):
	if ITransactionRecord.providedBy(records):
		records = (records,)
	history = ITransactionRecordHistory(target)
	history.extend(records)
	return len(records)
appendTransactions = append_transactions = append_records

def copy_transaction_history(source, target, clear=True):
	try:
		annotations = source.__annotations__
		source_history = annotations.pop(TRX_RECORD_HISTORY_KEY, None)
		if not source_history:
			return 0
		records = list(source_history.records())
		append_records(target, records)
		if clear:
			source_history.clear(event=False) # don't remove intids
		return len(records)
	except AttributeError:
		pass
	return 0
copyTransactionHistory = copy_history = copy_transaction_history

def copy_records(target, records=()):
	history = ITransactionRecordHistory(target)
	history.extend(records)
	return len(records)
copyRecords = copy_records
