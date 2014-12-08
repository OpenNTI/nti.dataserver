#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Interfaces related to catalogs.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import zope.catalog.keyword
from zope.catalog.interfaces import INoAutoIndex
from zope.catalog.interfaces import INoAutoReindex

class INoAutoIndexEver(INoAutoIndex, INoAutoReindex):
	"""
	Marker interface for objects that should not automatically
	be added to catalogs when created or modified events
	fire.
	"""

class IKeywordIndex(zope.catalog.keyword.IKeywordIndex):
	
	def ids():
		"""
		return the docids in this Index
		"""