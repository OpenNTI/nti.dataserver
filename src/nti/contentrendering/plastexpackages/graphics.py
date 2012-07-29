#!/usr/bin/env python
from __future__ import print_function, unicode_literals

from plasTeX import Command
from plasTeX.Packages.graphics import includegraphics,DeclareGraphicsExtensions,graphicspath

# SAJ: Adds a stub version of the \DeclareGraphicsRule command

class DeclareGraphicsRule(Command):
	packageName = 'graphics'
	args = '{extension:str}{type:str}{readfile:str}{command:str}'

