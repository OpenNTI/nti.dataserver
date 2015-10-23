#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

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

def get_connection(registry=None):
	registry = component.getSiteManager()
	result = IConnection(registry, None)
	return result

def add_2_connection(obj, connection=None):
	connection = get_connection() if connection is None else connection
	if connection is not None and IConnection(obj, None) is None:
		connection.add(object)

def principal():
	try:
		return getInteraction().participations[0].principal
	except (NoInteraction, IndexError, AttributeError):
		return None

def record_trax(recordable, descriptions=(), history=None):
	connection = get_connection()
	add_2_connection(recordable, connection)

	if history is None:
		history = ITransactionRecordHistory(recordable)
		add_2_connection(history, connection)

	tid = getattr(recordable, '_p_serial', None)
	tid = unicode(serial_repr(tid)) if tid else None

	attributes = set()
	for a in descriptions or ():
		attributes.update(a.attributes or ())

	username = principal().id
	record = TransactionRecord(principal=username, tid=tid,
							   attributes=tuple(attributes))
	history.add(record)

	recordable.locked = True
	return record

@component.adapter(IRecordable, IObjectModifiedFromExternalEvent)
def _record_modification(obj, event):
	if queryInteraction() is None:
		return
	history = ITransactionRecordHistory(obj, None)
	if history is None:
		return
	record_trax(obj, event.descriptions, history)
