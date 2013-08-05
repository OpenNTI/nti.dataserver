#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from plasTeX.Packages.graphicx import includegraphics  # Re-export

from . import graphics as _base_graphics

class DeclareGraphicsExtensions(_base_graphics.DeclareGraphicsExtensions):
	packageName = 'graphicx'

class DeclareGraphicsRule(_base_graphics.DeclareGraphicsRule):
	packageName = 'graphicx'

class graphicspath(_base_graphics.graphicspath):
	packageName = 'graphicx'
