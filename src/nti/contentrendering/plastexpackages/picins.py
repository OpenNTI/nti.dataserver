#!/usr/bin/env python
from __future__ import print_function, unicode_literals

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
