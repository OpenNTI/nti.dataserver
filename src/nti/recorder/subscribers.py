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

from ZODB.utils import u64

from nti.coremetadata.interfaces import IRecordable

from nti.externalization.interfaces import IObjectModifiedFromExternalEvent

from .record import TransactionRecord

from .interfaces import ITransactionRecordHistory

def principal():
	try:
		return getInteraction().participations[0].principal
	except (NoInteraction, IndexError, AttributeError):
		return None

def record_trax(obj, descriptions=(), history=None):
	history = ITransactionRecordHistory(obj) if history is None else history
	
	username = principal().id
	
	tid = getattr(obj, '_p_serial', None)
	tid = u64(tid) if tid else None
	
	attributes = set()
	for a in descriptions or ():
		attributes.update(a.attributes or ())
	record = TransactionRecord(principal=username, tid=tid,
							   attributes=tuple(attributes))
	history.add(record)
	return record

@component.adapter(IRecordable, IObjectModifiedFromExternalEvent)
def _record_modification(obj, event):
	if queryInteraction() is None:
		return
		
	history = ITransactionRecordHistory(obj, None)
	if history is None:
		return
	record_trax(obj, event.descriptions, history)
