#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from plasTeX import Command

# SAJ: Partial support for the picins package.

class picskip(Command):
	args = ' {text:int} '

	def invoke( self, tex ):
		# There's a {0} or so with this that we need to discard too
		# TODO: This may not be the best way
		tex.readGrouping( '{}' )
		return []

	def digest( self, tokens ):
		return super(picskip,self).digest( tokens )

class parpic(Command):
	args = '( size:dimen ) ( offset:dimen ) [Options:str] [Position] {Picture}'

	def invoke(self, tex):
		res = super( parpic, self).invoke(tex)

		return res
