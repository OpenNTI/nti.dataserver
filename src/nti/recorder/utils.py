#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import zlib
import pickle
from io import BytesIO

from zope import lifecycleevent

import transaction
try:
    from transaction._compat import get_thread_ident
except ImportError:
    def get_thread_ident():
        return id(transaction.get())

from nti.base._compat import unicode_

from nti.coremetadata.interfaces import IRecordable

from nti.coremetadata.utils import current_principal

from nti.externalization.externalization import isSyntheticKey

from nti.recorder.interfaces import TRX_TYPE_CREATE
from nti.recorder.interfaces import TRX_TYPE_UPDATE
from nti.recorder.interfaces import ITransactionRecordHistory

from nti.recorder.record import TransactionRecord

from ZODB.utils import serial_repr

principal = current_principal  # BWC


def compress(obj):
    __traceback_info__ = obj
    try:
        bio = BytesIO()
        pickle.dump(obj, bio)
        bio.seek(0)
        result = zlib.compress(bio.read())
        return result
    except Exception:  # seen in tests
        logger.exception("Cannot pickle/compress external object")
        return None


def decompress(source):
    data = zlib.decompress(source)
    bio = BytesIO(data)
    bio.seek(0)
    result = pickle.load(bio)
    return result


def is_created(obj):
    history = ITransactionRecordHistory(obj, None)
    if history is not None:
        records = history.query(record_type=TRX_TYPE_CREATE)
        return bool(records)
    return False


def txn_id():
    return unicode_("txn.%s" % get_thread_ident())


def _get_attributes(descriptions):
    if      descriptions is not None \
        and not isinstance(descriptions, (tuple, list, set)):
        descriptions = (descriptions,)

    result = set()

    def _accum(vals):
        # Exclude synthetic keys, including mimetype.
        for val in vals:
            if      val \
                and not isSyntheticKey(val) \
                and val.lower() != 'mimetype':
                result.add(val)

    for a in descriptions or ():
        if hasattr(a, 'attributes'):
            _accum(a.attributes or ())
        elif isinstance(a, (tuple, list, set)):
            _accum(a)
        else:
            _accum((a,))
    return result


def record_transaction(recordable, principal=None, descriptions=(),
                       ext_value=None, type_=TRX_TYPE_UPDATE, history=None,
                       lock=True, createdTime=None):
    __traceback_info__ = recordable, principal, ext_value
    attributes = _get_attributes(descriptions)
    if not attributes and type_ == TRX_TYPE_UPDATE:
        # Take care not to record anything that's not an actual edit.
        return

    if history is None:
        history = ITransactionRecordHistory(recordable)

    tid = getattr(recordable, '_p_serial', None)
    tid = unicode_(serial_repr(tid)) if tid else txn_id()
    tid = txn_id() if tid == u'0x00' else tid  # new object

    principal = current_principal(False) if principal is None else principal
    username = (   getattr(principal, 'id', None)
                or getattr(principal, 'usernane', None)
                or principal)

    if username is None:
        # Tests
        return

    # create record
    ext_value = compress(ext_value) if ext_value is not None else None
    record = TransactionRecord(principal=username, type=type_, tid=tid,
                               attributes=tuple(attributes),
                               external_value=ext_value)
    if createdTime is not None:
        record.lastModified = record.createdTime = createdTime
    lifecycleevent.created(record)
    # add - gain intid
    history.add(record)
    # mark locked
    if lock:
        if IRecordable.providedBy(recordable):
            recordable.lock()
        else:
            recordable.locked = True
    return record
recordTransaction = record_trax = record_transaction
