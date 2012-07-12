#!/usr/bin/env python
from __future__ import print_function, unicode_literals

import re, sys

from zope import interface

from nti.contentrendering import plastexids
from nti.contentrendering.resources import interfaces as res_interfaces

from plasTeX import Base
from plasTeX.Base.LaTeX import Index
from plasTeX.Packages import graphicx
from plasTeX.Base import Crossref
from plasTeX.Base import Node

###
# FIXME: star imports!
# If we don't, then we wind up with some rendering problems (at least the following):
# - unable to traverse to 'url' on an includegraphics
# - "No resource types for align* using default renderer <type 'unicode'>"
###
from plasTeX.Packages.fancybox import *
from plasTeX.Packages.graphicx import *
from plasTeX.Packages.amsmath import *

# SAJ: Partial support for the picins package.

class picskip(Base.Command):
	args = ' {text:int} '

	def invoke( self, tex ):
		# There's a {0} or so with this that we need to discard too
		# TODO: This may not be the best way
		tex.readGrouping( '{}' )
		return []

	def digest( self, tokens ):
		sys.stderr.write("Digesting: " + tokens + "\n" )
		return super(picskip,self).digest( tokens )

class parpic(Base.Command):
	args = '( size:dimen ) ( offset:dimen ) [Options:str] [Position] {Picture}'

	def invoke(self, tex):
		res = super( parpic, self).invoke(tex)

		return res
