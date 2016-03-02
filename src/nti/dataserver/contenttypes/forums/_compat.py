#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Various python3/pypy compatibility shims.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import zope.deferredimport
zope.deferredimport.initialize()

zope.deferredimport.deprecatedFrom(
	"Moved to nti.common._compat",
	"nti.common._compat",
	"IAcquirer",
	"Implicit",
	"Base",
	"aq_base")
