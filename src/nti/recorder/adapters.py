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

from zope.container.btree import BTreeContainer

from zope.location.location import locate

from ZODB.interfaces import IConnection

from nti.coremetadata.interfaces import IRecordable

from nti.recorder import TRX_RECORD_HISTORY_KEY

from nti.recorder.interfaces import ITransactionRecord
from nti.recorder.interfaces import ITransactionRecordHistory


@component.adapter(IRecordable)
@interface.implementer(ITransactionRecordHistory)
class TransactionRecordContainer(BTreeContainer):

    @property
    def object(self):
        return self.__parent__
    recordable = object

    def _do_add(self, record):
        key = record.key
        self._setitemf(key, record)
        locate(record, parent=self, name=key)
        if IConnection(record, None) is None:
            try:
                IConnection(self.object).add(record)
            except (TypeError, AttributeError):
                pass
        lifecycleevent.added(record, self, key)
        self._p_changed = True

    def add(self, record):
        assert ITransactionRecord.providedBy(record)
        self._do_add(record)  # avoid dublin container
        return record
    append = add

    def extend(self, records=()):
        for record in records or ():
            self.add(record)

    def remove(self, record):
        key = getattr(record, 'key', None) or str(record)
        del self[key]

    def records(self):
        return list(self.values())

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

    def query(self, tid=None, principal=None, record_type=None):
        results = []
        for record in self.records():
            if      (not tid or tid == record.tid) \
                and (not principal or principal == record.principal) \
                and (not record_type or record_type == record.type):
                results.append(record)
        return results

_TransactionRecordHistoryFactory = an_factory(TransactionRecordContainer,
                                              TRX_RECORD_HISTORY_KEY)


def TransactionRecordHistoryFactory(obj):
    result = _TransactionRecordHistoryFactory(obj)
    if IConnection(result, None) is None:
        try:
            IConnection(obj).add(result)
        except (TypeError, AttributeError):
            pass
    return result
