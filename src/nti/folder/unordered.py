#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from Acquisition import aq_base

from zope.component import adapter

from zope.interface import implementer

from .interfaces import IOrdering
from .interfaces import IOrderableFolder

@implementer(IOrdering)
@adapter(IOrderableFolder)
class UnorderedOrdering(object):

	def __init__(self, context):
		self.context = context

	def notifyAdded(self, obj_id):
		pass

	def notifyRemoved(self, obj_id):
		pass

	def idsInOrder(self):
		return aq_base(self.context).objectIds(ordered=False)

	def getObjectPosition(self, obj_id):
		return None
