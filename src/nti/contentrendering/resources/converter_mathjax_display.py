#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import re
import cgi

from nti.contentrendering.resources import converter_mathjax_inline

class MathjaxDisplayCompilerDriver(converter_mathjax_inline.MathjaxInlineCompilerDriver):

	def _compilation_source_for_content_unit( self, content_unit ):
		# Filter spaceing / formatting bits that MathJax does not handle
		tex = re.sub(r'\[[0-9][0-9]*ex\]', '', content_unit.source)
		scaped = cgi.escape(tex)
		return '<span class="mathjax math tex2jax_process">%s</span>\n\n' % scaped

class MathjaxDisplayBatchConverter(converter_mathjax_inline.MathjaxInlineBatchConverter):

	resourceType = 'mathjax_display'
	compiler_driver = MathjaxDisplayCompilerDriver

ResourceSetGenerator = MathjaxDisplayCompilerDriver
ResourceGenerator = MathjaxDisplayBatchConverter

from zope.deprecation import deprecated
deprecated(['ResourceGenerator', 'ResourceSetGenerator'], 'Prefer the new names in this module')
