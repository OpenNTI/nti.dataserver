#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from zope.container.contained import Contained

from zope.deprecation import deprecated

from zope.mimetype.interfaces import IContentTypeAware

from persistent import Persistent

from nti.common.property import alias

from nti.dublincore.datastructures import PersistentCreatedModDateTrackingObject

from nti.externalization.representation import WithRepr

from nti.schema.schema import EqHash
from nti.schema.field import SchemaConfigured
from nti.schema.fieldproperty import createDirectFieldProperties

from .interfaces import TRX_RECORD_HISTORY_KEY

from .interfaces import ITransactionRecord
from .interfaces import ITransactionRecordHistory

@WithRepr
@EqHash('principal', 'createdTime', 'tid')
@interface.implementer(ITransactionRecord, IContentTypeAware)
class TransactionRecord(PersistentCreatedModDateTrackingObject,
			 			SchemaConfigured,
			 			Contained):

	createDirectFieldProperties(ITransactionRecord)

	serial = alias('tid')
	username = alias('principal')

	def __init__(self, *args, **kwargs):
		SchemaConfigured.__init__(self, *args, **kwargs)
		PersistentCreatedModDateTrackingObject.__init__(self)

	@property
	def key(self):
		return "(%s,%s,%s)" % (self.createdTime, self.principal, self.tid)

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

def get_transactions(obj, sort=False, descending=True):
	result = []
	try:
		annotations = obj.__annotations__
		history = annotations.get(TRX_RECORD_HISTORY_KEY, None)
		result.extend(history or ())
		if sort:
			result.sort(key=lambda t: t.createdTime, reverse=descending)
	except AttributeError:
		pass
	return result

def remove_history(obj):
	try:
		annotations = obj.__annotations__
		history = annotations.pop(TRX_RECORD_HISTORY_KEY, None)
		if history:
			return history.clear()
	except AttributeError:
		pass
	return 0
remove_transaction_history = remove_history

def append_records(target, records=()):
	if ITransactionRecord.providedBy(records):
		records = (records,)
	history = ITransactionRecordHistory(target)
	history.extend(records)
	return len(records)
append_transactions = append_records

def copy_history(source, target, clear=True):
	try:
		annotations = source.__annotations__
		source_history = annotations.pop(TRX_RECORD_HISTORY_KEY, None)
		if not source_history:
			return 0
		records = list(source_history)
		target_history = ITransactionRecordHistory(target)
		target_history.extend(records)
		if clear:
			source_history.clear(event=False)
		return len(records)
	except AttributeError:
		pass
	return 0
copy_transaction_history = copy_history

def copy_records(target, records=()):
	history = ITransactionRecordHistory(target)
	history.extend(records)
	return len(records)
