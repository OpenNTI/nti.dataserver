#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

from plasTeX import Command

# for export
from plasTeX.Packages.graphics import graphicspath
from plasTeX.Packages.graphics import includegraphics
from plasTeX.Packages.graphics import _locate_image_file
from plasTeX.Packages.graphics import DeclareGraphicsExtensions

# SAJ: Adds a stub version of the \DeclareGraphicsRule command

class DeclareGraphicsRule(Command):
	packageName = 'graphics'
	args = '{extension:str}{type:str}{readfile:str}{command:str}'
