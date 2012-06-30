#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals


import cgi

from nti.contentrendering.resources import converter_mathjax_inline

class MathjaxDisplayCompilerDriver(converter_mathjax_inline.MathjaxInlineCompilerDriver):

	def writeResource(self, source):
		self.writer.write( '\n' )
		self.writer.write('<span class="mathjax math tex2jax_process mathquill-embedded-latex">' )
		self.writer.write( cgi.escape( source ) )
		self.writer.write( '</span>\n\n' )


class MathjaxDisplayBatchConverter(converter_mathjax_inline.MathjaxInlineBatchConverter):

	resourceType = 'mathjax_display'
	compiler_driver = MathjaxDisplayCompilerDriver


ResourceSetGenerator = MathjaxDisplayCompilerDriver
ResourceGenerator = MathjaxDisplayBatchConverter

from zope.deprecation import deprecated
deprecated( ['ResourceGenerator','ResourceSetGenerator'], 'Prefer the new names in this module' )
