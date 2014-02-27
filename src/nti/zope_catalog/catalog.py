#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Catalog extensions.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope.catalog.catalog import Catalog as _ZCatalog
from .interfaces import INoAutoIndex

class Catalog(_ZCatalog):
	"""
	An extended catalog. Features include:

	* When manually calling :meth:`updateIndex` or :meth:`updateIndexes`,
	  objects that provide :class:`.INoAutoIndex` are ignored.
	  Note that if you have previously indexed objects that now provide
	  this (i.e., class definition has changed) you need to :meth:`clear`
	  the catalog first for this to be effective.
	"""

	def _visitSublocations(self):
		for uid, obj in super(Catalog,self)._visitSublocations():
			if INoAutoIndex.providedBy(obj):
				continue
			yield uid, obj
