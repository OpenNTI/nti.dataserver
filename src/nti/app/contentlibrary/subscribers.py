#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from nti.contentlibrary.interfaces import IContentPackageLibrary
from nti.contentlibrary.interfaces import IContentPackageBundleLibrary
from nti.contentlibrary.interfaces import IContentPackageLibraryDidSyncEvent

from nti.site.interfaces import IHostPolicySiteManager

from .interfaces import IContentBoard

@component.adapter(IContentPackageLibrary, IContentPackageLibraryDidSyncEvent)
def _on_content_pacakge_library_synced(library, event):
	site  = library.__parent__
	if IHostPolicySiteManager.providedBy(site):
		bundle_library = site.getUtility(IContentPackageBundleLibrary)
		for bundle in bundle_library.values():
			board = IContentBoard(bundle, None)
			if board is not None:
				board.createDefaultForum()
