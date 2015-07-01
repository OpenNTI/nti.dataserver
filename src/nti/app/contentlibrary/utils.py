#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from nti.contentlibrary.indexed_data import get_catalog

from nti.contentlibrary.interfaces import IContentUnit
from nti.contentlibrary.interfaces import IContentPackageLibrary

from nti.ntiids.ntiids import find_object_with_ntiid

def get_content_untis(ntiids=()):
	result = []
	library = component.queryUtility(IContentPackageLibrary)
	if library is not None:
		for ntiid in ntiids or ():
			context = find_object_with_ntiid(ntiid)
			if not IContentUnit.providedBy(context):
				context = IContentUnit(context, None)
			if context is not None:
				result.append(context)
		return result

def get_presentation_asset_content_units(item, sort=False):
	catalog = get_catalog()
	entries = catalog.get_containers(item)
	result = get_content_untis(entries) if entries else ()
	return result
