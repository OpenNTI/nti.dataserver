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

from dolmen.builtins.interfaces import IIterable

from nti.dataserver_core.interfaces import ICreated

from nti.schema.field import ValidTextLine
from nti.schema.field import IndexedIterable

class ITransactionRecord(IContained, ICreated):
	tid = ValidTextLine(title="The transaction/serial id", required=False)
	principal = ValidTextLine(title="The principal id", required=True)
	attributes = IndexedIterable(title="The modifed attributes",
				 	 			 value_type=ValidTextLine(title="The attribute name"),
								 min_length=1,
								 unique=True)
	external_value = interface.Attribute("External value")
	external_value.setTaggedValue('_ext_excluded_out', True)

class ITransactionRecordHistory(IContained, IIterable):

	def add(record):
		pass

	def extend(records):
		pass

	def remove(record):
		pass

	def clear(event=True):
		pass
