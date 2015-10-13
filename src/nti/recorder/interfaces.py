#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope.container.interfaces import IContained

from dolmen.builtins.interfaces import IIterable

from nti.dataserver_core.interfaces import ICreated

from nti.schema.field import Set
from nti.schema.field import ValidTextLine

class ITransactionRecord(IContained, ICreated):
	tid = ValidTextLine(title="The transaction/serial id", required=False)
	creator = ValidTextLine(title="The attribute name", required=True)
	attributes = Set(title="The modifed attributes",
				 	 value_type=ValidTextLine(title="The attribute name"),
					 min_length=1)

class ITransactionRecordHistory(IContained, IIterable):

	def add(record):
		pass

	def remove(record):
		pass

	def clear(self):
		pass
