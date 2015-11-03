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

from zope.annotation import factory as an_factory

from zope.container.btree import BTreeContainer

from nti.coremetadata.interfaces import IRecordable

from .interfaces import ITransactionRecord
from .interfaces import ITransactionRecordHistory

from . import TRX_RECORD_HISTORY_KEY

@component.adapter(IRecordable)
@interface.implementer(ITransactionRecordHistory)
class TransactionRecordContainer(BTreeContainer):

	@property
	def object(self):
		return self.__parent__
	recordable = object

	def add(self, record):
		assert ITransactionRecord.providedBy(record)
		self[record.key] = record
		return record
	append = add

	def extend(self, records=()):
		for record in records or ():
			self.add(record)

	def remove(self, record):
		key = getattr(record, 'key', str(record))
		del self[key]

	def records(self):
		return iter(self.values())

	def _delitemf(self, key):
		l = self._BTreeContainer__len
		item = self._SampleContainer__data[key]
		del self._SampleContainer__data[key]
		l.change(-1)
		return item
		
	def clear(self, event=True):
		keys = list(self.keys())
		for key in keys:
			if event:
				del self[key]
			else:
				self._delitemf(key)
		return len(keys)
	reset = clear

_TransactionRecordHistoryFactory = an_factory(TransactionRecordContainer,
											  TRX_RECORD_HISTORY_KEY)