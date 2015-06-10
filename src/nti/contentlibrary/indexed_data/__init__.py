#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Indexed data is associated with content units and is typically
extracted at content rendering time.

It is typically accessed by adapting content units to the interfaces
of this package.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from .interfaces import IContainedObjectCatalog

CATALOG_INDEX_NAME = '++etc++contentlibrary.container_index'

def get_catalog():
	result = component.queryUtility(IContainedObjectCatalog, name=CATALOG_INDEX_NAME)
	return result
get_index = get_catalog
