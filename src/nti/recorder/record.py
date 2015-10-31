#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component
from zope import interface
from zope import lifecycleevent

from zope.annotation import factory as an_factory

from zope.container.contained import Contained

from zope.location import locate
from zope.location.interfaces import ISublocations

from zope.mimetype.interfaces import IContentTypeAware

from ZODB.interfaces import IConnection

from persistent import Persistent
from persistent.list import PersistentList

from nti.common.property import alias

from nti.coremetadata.interfaces import IRecordable

from nti.dublincore.datastructures import PersistentCreatedModDateTrackingObject

from nti.externalization.representation import WithRepr

from nti.schema.schema import EqHash
from nti.schema.field import SchemaConfigured
from nti.schema.fieldproperty import createDirectFieldProperties

from .interfaces import ITransactionRecord
from .interfaces import ITransactionRecordHistory

@WithRepr
@EqHash('principal', 'createdTime')
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

	def key(self):
		return "(%s,%s,%s)" % (self.principal, self.createdTime, self.tid)

@component.adapter(IRecordable)
@interface.implementer(ITransactionRecordHistory, ISublocations)
class TransactionRecordHistory(Contained, Persistent):

	def __init__(self):
		self.reset()

	def reset(self):
		self._records = PersistentList()
		self._records.__parent__ = self

	@property
	def object(self):
		return self.__parent__

	def add(self, record, connection=True):
		assert ITransactionRecord.providedBy(record)
		locate(record, self) # take ownership
		if connection:
			if getattr(record, '_p_jar', None) is None:
				IConnection(self).add(record)
				lifecycleevent.created(record)
			lifecycleevent.added(record)  # get an iid
		self._records.append(record)
		return record
	append = add

	def extend(self, records=(), connection=False):
		for record in records or ():
			self.add(record, connection=connection)

	def remove(self, record, event=True):
		self._records.remove(record)
		if event:
			lifecycleevent.removed(record)  # remove iid
		return True

	def clear(self, event=True):
		result = len(self._records)
		if not event:
			del self._records[:]
		else:
			for _ in xrange(len(self._records)):
				record = self._records.pop()
				lifecycleevent.removed(record)  # remove iid
		return result

	def __iter__(self):
		return iter(self._records)

	def __len__(self):
		return len(self._records)

	def sublocations(self):
		for record in self._records:
			yield record

TRX_RECORD_HISTORY_KEY = 'nti.recorder.record.TransactionRecordHistory'
_TransactionRecordHistoryFactory = an_factory(TransactionRecordHistory,
											  TRX_RECORD_HISTORY_KEY)

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

def append_records(target, records=(), connection=True):
	if ITransactionRecord.providedBy(records):
		records = (records,)
	history = ITransactionRecordHistory(target)
	history.extend(records, connection)
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

def copy_records(target, records=(), connection=False):
	history = ITransactionRecordHistory(target)
	history.extend(records, connection)
	return len(records)
