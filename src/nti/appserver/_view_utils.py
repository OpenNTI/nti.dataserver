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
	"Moved to nti.app.externalization.view_mixins",
	"nti.app.externalization.view_mixins",
	"UploadRequestUtilsMixin",
	"ModeledContentUploadRequestUtilsMixin",
	"ModeledContentEditRequestUtilsMixin")

zope.deferredimport.deprecatedFrom(
	"Moved to nti.app.authentication",
	"nti.app.authentication",
	"get_remote_user")

zope.deferredimport.deprecatedFrom(
	"Moved to nti.app.base.abstract_views",
	"nti.app.base.abstract_views",
	"AbstractView",
	"AbstractAuthenticatedView")
