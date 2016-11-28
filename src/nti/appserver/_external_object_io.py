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
	"Moved to nti.app.externalization.internalization",
	"nti.app.externalization.internalization",
	"create_modeled_content_object",
	"class_name_from_content_type",
	"read_body_as_external_object",
	"update_object_from_external_object")

zope.deferredimport.deprecatedFrom(
	"Moved to nti.app.externalization.error",
	"nti.app.externalization.error",
	"handle_possible_validation_error",
	"handle_validation_error")
