#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from plasTeX.Packages.graphics import graphicspath as BaseGraphicspath
from plasTeX.Packages.graphics import DeclareGraphicsExtensions as BaseDeclareGraphicsExtensions

from .graphics import DeclareGraphicsRule as BaseDeclareGraphicsRule

class DeclareGraphicsExtensions(BaseDeclareGraphicsExtensions):
	packageName = 'graphicx'

class DeclareGraphicsRule(BaseDeclareGraphicsRule):
	packageName = 'graphicx'

class graphicspath(BaseGraphicspath):
	packageName = 'graphicx'

import zope.deferredimport
zope.deferredimport.initialize()

zope.deferredimport.deprecatedFrom(
    "Moved to plasTeX.Packages.graphicx",
    "plasTeX.Packages.graphicx",
    "includegraphics")
