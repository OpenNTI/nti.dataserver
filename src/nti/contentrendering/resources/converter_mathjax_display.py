#!/usr/bin/env python2.7

import cgi

from nti.contentrendering.resources import converter_mathjax_inline as tex2html

class ResourceSetGenerator(tex2html.ResourceSetGenerator):

	def writeResource(self, source):
		self.writer.write('%s<span class="mathjax math tex2jax_process mathquill-embedded-latex">%s</span>\n\n' %
						 ('' , cgi.escape(source)))

class ResourceGenerator(tex2html.ResourceGenerator):

	resourceType = 'mathjax_display'

	def _new_batch_compile_driver(self, document, compiler='', encoding='utf-8', batch=0):
		result = ResourceSetGenerator( document, compiler, encoding, batch)
		result.resourceType = self.resourceType
		return result
