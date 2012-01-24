#!/usr/bin/env python2.7

import cgi
import tex2html

class ResourceSetGenerator(tex2html.ResourceSetGenerator):

	def writeResource(self, source, context):
		self.writer.write('%s<span class="mathjax math tex2jax_process mathquill-embedded-latex">%s</span>\n\n' %
						 (context , cgi.escape(source)))

class ResourceGenerator(tex2html.ResourceGenerator):

	resourceType = 'mathjax_display'

	def createResourceSetGenerator(self, compiler='', encoding='utf-8', batch=0):
		return ResourceSetGenerator(compiler, encoding, batch)

def _processBatchSource(generator, sourceConfigPath):
	if generator.size() > 0:
		return generator.processSource()
	else:
		return ()



