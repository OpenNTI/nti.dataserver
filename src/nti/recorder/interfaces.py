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

from nti.schema.field import Bool
from nti.schema.field import Dict
from nti.schema.field import Date
from nti.schema.field import Text
from nti.schema.field import Number
from nti.schema.field import Variant
from nti.schema.field import TextLine
from nti.schema.field import DateTime
from nti.schema.field import Timedelta
from nti.schema.field import ValidTextLine

class IRecord(IContained, ICreated):
	creator = ValidTextLine(title="The attribute name", required=True)
	attributes = Dict(title="The modifed attributes",
				 	  key_type=ValidTextLine(title="The attribute name"),
					  value_type=
					  		Variant((Number(title="Number value"),
							   		 Bool(title='Boolean value'),
							   		 Date(title='Date value'),
							   		 Text(title='Text value'),
							   		 DateTime(title='Datetime value'),
							   		 Timedelta(title='Timedelta value'),
							   		 TextLine(title='String value'),), title="The value"),
					  min_length=1)

class IRecordHistory(IContained, IIterable):
	
	def add(record):
		pass
	
	def remove(record):
		pass
	
	def clear(self):
		pass
