#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
See nti.app.contentlibrary.library_views

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

#########
# IMPORTANT NOTE: This module cannot go away when all deprecations are removed.
# It used to contain a persistent object stored in annotations, so
# import compatibility has to be maintained.
#########

import zope.deferredimport
zope.deferredimport.initialize()

zope.deferredimport.deprecatedFrom(
	"Moved to nti.app.contentlibrary.content_unit_preferences",
	"nti.app.contentlibrary.content_unit_preferences.adapters",
	# ZODB persistent objects compat
	"_ContentUnitPreferences")

zope.deferredimport.deprecatedFrom(
	"Moved to nti.app.contentlibrary.library_views",
	"nti.app.contentlibrary.library_views",
	"PAGE_INFO_MT",
	"PAGE_INFO_MT_JSON",
	"find_page_info_view_helper")
