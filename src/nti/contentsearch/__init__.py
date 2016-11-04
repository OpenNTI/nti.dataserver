#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import zope.i18nmessageid
MessageFactory = zope.i18nmessageid.MessageFactory('nti.dataserver')

import zope.deferredimport
zope.deferredimport.initialize()

zope.deferredimport.deprecatedFrom(
    "Moved to nti.contentsearch.common",
    "nti.contentsearch.common",
    "get_indexable_types",
    "get_ugd_indexable_types",
    "videotimestamp_to_datetime")

zope.deferredimport.deprecatedFrom(
    "Moved to nti.contentsearch.constants",
    "nti.contentsearch.constants",
    "vtrans_prefix",
    "nticard_prefix")
