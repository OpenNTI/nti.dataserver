#!/usr/bin/env python
"""
$Id$
"""

from __future__ import absolute_import, unicode_literals, print_function

from . import graphics as _base_graphics
from plasTeX.Packages.graphicx import includegraphics # Re-export

class DeclareGraphicsExtensions(_base_graphics.DeclareGraphicsExtensions):
	packageName = 'graphicx'

class DeclareGraphicsRule(_base_graphics.DeclareGraphicsRule):
	packageName = 'graphicx'

class graphicspath(_base_graphics.graphicspath):
	packageName = 'graphicx'
