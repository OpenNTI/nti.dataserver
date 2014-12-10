#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

# Necesary Rexport
from plasTeX.Packages.graphics import graphicspath
from plasTeX.Packages.graphics import includegraphics
from plasTeX.Packages.graphics import DeclareGraphicsExtensions

graphicspath = graphicspath
includegraphics = includegraphics
DeclareGraphicsExtensions = DeclareGraphicsExtensions

# Necesary Rexport
from plasTeX.Packages.graphics import _locate_image_file
_locate_image_file = _locate_image_file

from plasTeX import Command

# Adds a stub version of the \DeclareGraphicsRule command
class DeclareGraphicsRule(Command):
	packageName = 'graphics'
	args = '{extension:str}{type:str}{readfile:str}{command:str}'
