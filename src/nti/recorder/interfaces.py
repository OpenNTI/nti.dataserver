#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from zope.container.interfaces import IContained

from nti.base.interfaces import ICreated
from nti.base.interfaces import ILastModified

from nti.schema.field import Object
from nti.schema.field import TextLine
from nti.schema.field import IndexedIterable

TRX_RECORD_HISTORY_KEY = 'nti.recorder.record.TransactionRecordHistory'

#: Created Transaction type
TRX_TYPE_CREATE = 'create'

#: Updated Transaction type
TRX_TYPE_UPDATE = 'update'


class ITransactionRecord(IContained, ICreated, ILastModified):
    tid = TextLine(title="The transaction/serial id", required=False)

    type = TextLine(title="The transaction type",
                         required=False,
                         default=TRX_TYPE_UPDATE)

    principal = TextLine(title="The principal id", required=True)

    attributes = IndexedIterable(title="The modifed attributes",
                                 value_type=TextLine(title="The attribute name"),
                                 min_length=0,
                                 unique=True)

    external_value = Object(interface.Interface,
                            title="External value",
                            required=False)
    external_value.setTaggedValue('_ext_excluded_out', True)

    key = interface.Attribute('record key')
    key.setTaggedValue('_ext_excluded_out', True)


class ITransactionRecordHistory(IContained):

    def add(record):
        pass

    def extend(records):
        pass

    def remove(record):
        pass

    def clear(event=True):
        pass

    def records():
        pass

    def query(self, tid=None, principal=None, record_type=None):
        """
        Query the transaction history for record(s) matching
        the given filters.
        """
