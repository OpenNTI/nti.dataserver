#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

# Import all items from aopsbook.py.
# This file is our central file for all AoPS specific macros.
from .aopsbook import *

import zope.deferredimport
zope.deferredimport.initialize()

zope.deferredimport.deprecatedFrom(
    "Moved to nti.contentrendering.plastexpackages.graphicx",
    "nti.contentrendering.plastexpackages.graphicx",
    "graphicspath",
    "includegraphics",
    "DeclareGraphicsRule",
    "DeclareGraphicsExtensions")


