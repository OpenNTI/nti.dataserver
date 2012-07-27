#!/usr/bin/env python
from __future__ import print_function, unicode_literals

from plasTeX.Packages.graphicx import includegraphics,DeclareGraphicsExtensions,graphicspath
from nti.contentrendering.plastexpackages.graphics import DeclareGraphicsRule as _DeclareGraphicsRule

# SAJ: Adds a stub version of the \DeclareGraphicsRule command

class DeclareGraphicsRule(_DeclareGraphicsRule):
	packageName = 'graphicx'
