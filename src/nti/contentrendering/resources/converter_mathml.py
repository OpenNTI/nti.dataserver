#!/usr/bin/env python
import logging
logger = logging.getLogger( __name__ )

import codecs
import os
import re
import sys


import xml.sax
from xml.sax.xmlreader import InputSource
from xml.dom import minidom
#from plasTeX.Imagers import *

import nti.contentrendering.resources as resources
from . import interfaces, converters

def findfile(path):
	for dirname in sys.path:
		possible = os.path.join(dirname, path)
		if os.path.isfile(possible):
			return possible
	return None

class MyEntityResolver(xml.sax.handler.EntityResolver):

	def resolveEntity(self, p, s):

		name = s.split('/')[-1:][0]

		print 'looking for local source %s' % name
		local = findfile(name)

		if local:
			print 'Using local source'
			return InputSource(local)

		return InputSource(s)


_RESOURCE_TYPE = 'mathml'

class ResourceSetGenerator(converters.AbstractLatexCompilerDriver):

	fileExtension = '.xml'
	resourceType = _RESOURCE_TYPE

	def convert(self, output, workdir):

		i = 0
		resourceNames = []
		dom = self.buildMathMLDOM(output)
		mathmls = dom.getElementsByTagName('math')

		for mathml in mathmls:
			resource = '%s_%s%s' % (self.resourceType, i, self.fileExtension)
			fpath = os.path.join(workdir, resource)
			with codecs.open(fpath, 'w', self.encoding) as f:
				f.write(mathml.toxml())
			resourceNames.append(resource)
			i = i + 1

		return [resources.Resource(os.path.join(workdir, name)) for name in resourceNames]

	def buildMathMLDOM(self, output):
		# Load up the results into a dom
		parser = xml.sax.make_parser()
		parser.setEntityResolver(MyEntityResolver())

		return minidom.parse(output, parser)

class ResourceGenerator(converters.AbstractConcurrentCompilingContentUnitRepresentationBatchConverter):

	debug			= False

	concurrency		= 4
	compiler		= 'ttm'
	resourceType  	= _RESOURCE_TYPE
	illegalCommands	= [	'\\\\overleftrightarrow',\
					 	'\\\\vv',\
					 	'\\\\smash',\
					 	'\\\\rlin',\
					 	'\\\\textregistered']

	def _new_batch_compile_driver(self, document, compiler='', encoding='utf-8', batch=0):
		return ResourceSetGenerator(document, self.compiler, encoding, batch)

	def _can_process(self, content_unit):
		if not self.illegalCommands:
			return True

		source = content_unit.source
		for command in self.illegalCommands:
			if re.search(command, source):
				return False
		return True
