#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Interfaces related to catalogs.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope.catalog.interfaces import INoAutoIndex
from zope.catalog.interfaces import INoAutoReindex
from zope.catalog.interfaces import ICatalog

class INoAutoIndexEver(INoAutoIndex, INoAutoReindex):
	"""
	Marker interface for objects that should not automatically
	be added to catalogs when created or modified events
	fire.
	"""

class IMetadataCatalog(ICatalog):
	"""
	The nti metadata catalog.
	"""

	def index_doc(self, id, ob):
		"""
		This may or may not update our underlying index.
		"""

	def force_index_doc(self, id, ob):
		"""
		Force the underlying index to update.
		"""
