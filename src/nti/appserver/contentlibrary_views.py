#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import zope.deferredimport
zope.deferredimport.initialize()

zope.deferredimport.deprecatedFrom(
    "Moved to nti.app.contentlibrary.content_unit_preferences",
    "nti.app.contentlibrary.content_unit_preferences.adapters",
    "_ContentUnitPreferences")

# Restore (partial) backwards compatibility with old
# ZODB pickles. This is only partial because, while we can
# fix the imports, fixing the annotation factory keys, which are
# now a mix of the 'old' keys from this location and the 'new'
# keys from the moved location is a bit more complex. Fortunately,
# nobody seemed to notice that their preferences disappeared,
# so the only real issue here is the broken pickles
import zope.deprecation
zope.deprecation.moved('nti.app.contentlibrary.views.library_views')
