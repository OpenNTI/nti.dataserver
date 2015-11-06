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

from nti.dataserver_core.interfaces import ICreated

from nti.schema.field import Object
from nti.schema.field import ValidTextLine
from nti.schema.field import IndexedIterable

TRX_RECORD_HISTORY_KEY = 'nti.recorder.record.TransactionRecordHistory'

class ITransactionRecord(IContained, ICreated):
	tid = ValidTextLine(title="The transaction/serial id", required=False)
	principal = ValidTextLine(title="The principal id", required=True)
	attributes = IndexedIterable(title="The modifed attributes",
				 	 			 value_type=ValidTextLine(title="The attribute name"),
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

