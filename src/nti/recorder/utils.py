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
from zope.security.interfaces import NoInteraction
from zope.security.management import getInteraction

import transaction
try:
	from transaction._compat import get_thread_ident
except ImportError:
	def get_thread_ident():
		return id(transaction.get())

from .interfaces import TRX_TYPE_CREATE
from .interfaces import TRX_TYPE_UPDATE
from .interfaces import ITransactionRecordHistory

from .record import TransactionRecord

from ZODB.utils import serial_repr

def compress(obj):
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

def current_principal():
	try:
		return getInteraction().participations[0].principal
	except (NoInteraction, IndexError, AttributeError):
		return None
principal = current_principal

def is_created(obj):
	history = ITransactionRecordHistory(obj, None)
	if history is not None:
		records = history.query(record_type=TRX_TYPE_CREATE)
		return bool(records)
	return False

def txn_id():
	return unicode("txn.%s" % get_thread_ident())

def record_transaction(recordable, principal=None, descriptions=(),
					   ext_value=None, type_=TRX_TYPE_UPDATE, history=None):

	__traceback_info__ = recordable, principal, ext_value

	if history is None:
		history = ITransactionRecordHistory(recordable)

	tid = getattr(recordable, '_p_serial', None)
	tid = unicode(serial_repr(tid)) if tid else txn_id()
	tid = txn_id() if tid == u'0x00' else tid  # new object

	if descriptions is not None and not isinstance(descriptions, (tuple, list, set)):
		descriptions = (descriptions,)

	attributes = set()
	for a in descriptions or ():
		if hasattr(a, 'attributes'):
			attributes.update(a.attributes or ())
		elif isinstance(a, (tuple, list, set)):
			attributes.update(a)
		else:
			attributes.add(a)

	principal = current_principal() if principal is None else principal
	username = (getattr(principal, 'id', None)
				or	getattr(principal, 'usernane', None)
				or	principal)
	ext_value = compress(ext_value) if ext_value is not None else None
	record = TransactionRecord(principal=username, type=type_, tid=tid,
							   attributes=tuple(attributes),
							   external_value=ext_value)
	lifecycleevent.created(record)
	history.add(record)

	recordable.locked = True
	return record
recordTransaction = record_trax = record_transaction
