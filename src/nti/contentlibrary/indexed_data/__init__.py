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

import time

from zope import component

from nti.contentlibrary.indexed_data.interfaces import IContainedObjectCatalog

from nti.contentlibrary.interfaces import IContentPackageLibrary
from nti.contentlibrary.interfaces import IGlobalContentPackageLibrary

# catalog
CATALOG_INDEX_NAME = '++etc++contentlibrary.container_index'

def get_library_catalog():
	result = component.queryUtility(IContainedObjectCatalog, name=CATALOG_INDEX_NAME)
	return result
get_catalog = get_library_catalog

def get_site_registry(registry=None):
	if registry is None:
		library = component.queryUtility(IContentPackageLibrary)
		if IGlobalContentPackageLibrary.providedBy(library):
			registry = component.getGlobalSiteManager()
		else:
			registry = component.getSiteManager()
	return registry
registry = get_registry = get_site_registry
