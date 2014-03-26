#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from plasTeX import Command

# Adds a stub version of the \DeclareGraphicsRule command
class DeclareGraphicsRule(Command):
	packageName = 'graphics'
	args = '{extension:str}{type:str}{readfile:str}{command:str}'

import zope.deferredimport
zope.deferredimport.initialize()

zope.deferredimport.deprecatedFrom(
    "Moved to plasTeX.Packages.graphics",
    "plasTeX.Packages.graphics",
    "graphicspath",
    "includegraphics",
    "DeclareGraphicsExtensions",
    "_locate_image_file")
