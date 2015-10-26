#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import zlib
from io import BytesIO

from zope import component

from zope.security.interfaces import NoInteraction
from zope.security.management import getInteraction
from zope.security.management import queryInteraction

from ZODB.utils import serial_repr

from ZODB.interfaces import IConnection

from nti.coremetadata.interfaces import IRecordable

from nti.externalization.interfaces import IObjectModifiedFromExternalEvent

from .record import TransactionRecord

from .interfaces import ITransactionRecordHistory

def principal():
	try:
		return getInteraction().participations[0].principal
	except (NoInteraction, IndexError, AttributeError):
		return None

def pickle(obj):
	bio = BytesIO()
	pickle.dump(obj, bio)
	bio.seek(0)
	result = zlib.compress(bio.read())
	return result
	
def record_trax(recordable, descriptions=(), ext_value=None, history=None):
	if history is None:
		history = ITransactionRecordHistory(recordable)

	tid = getattr(recordable, '_p_serial', None)
	tid = unicode(serial_repr(tid)) if tid else None

	attributes = set()
	for a in descriptions or ():
		attributes.update(a.attributes or ())

	username = principal().id
	ext_value = pickle(ext_value) if ext_value is not None else None
	record = TransactionRecord(principal=username, tid=tid,
							   attributes=tuple(attributes),
							   external_value=ext_value)
	history.add(record)

	recordable.locked = True
	return record

@component.adapter(IRecordable, IObjectModifiedFromExternalEvent)
def _record_modification(obj, event):
	# XXX: don't process if batch update or new object
	if queryInteraction() is None or IConnection(obj, None) is None:
		return
	history = ITransactionRecordHistory(obj)
	record_trax(obj, event.descriptions, event.external_value, history)
