#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A resource converter to create MathXML.

..note:: This module is currently not used or tested.

$Id$
"""
from __future__ import print_function, unicode_literals

logger = __import__('logging').getLogger(__name__)

import codecs
import os
import sys


import xml.sax
from xml.sax.xmlreader import InputSource
from xml.dom import minidom
#from plasTeX.Imagers import *

import nti.contentrendering.resources as resources
from . import converters

def findfile(path):
	for dirname in sys.path:
		possible = os.path.join(dirname, path)
		if os.path.isfile(possible):
			return possible
	return None

class MyEntityResolver(xml.sax.handler.EntityResolver):

	def resolveEntity(self, p, s):

		name = s.split('/')[-1:][0]
		local = findfile(name)

		if local:
			return InputSource(local)

		return InputSource(s)


_RESOURCE_TYPE = 'mathml'

class XMLMathCompilerDriver(converters.AbstractLatexCompilerDriver):

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

class TTMBatchConverter(converters.AbstractConcurrentConditionalCompilingContentUnitRepresentationBatchConverter):
	"""
	Converts by compiling latex using the TTM command.
	"""

	concurrency		= 4
	compiler		= 'ttm'
	resourceType  	= _RESOURCE_TYPE
	illegalCommands	= [	'\\\\overleftrightarrow',\
					 	'\\\\vv',\
					 	'\\\\smash',\
					 	'\\\\rlin',\
					 	'\\\\textregistered']

	def _new_batch_compile_driver(self, document, compiler='', encoding='utf-8', batch=0):
		return XMLMathCompilerDriver(document, self.compiler, encoding, batch)

ResourceGenerator = TTMBatchConverter
ResourceSetGenerator = XMLMathCompilerDriver

from zope.deprecation import deprecated
deprecated( ['ResourceGenerator','ResourceSetGenerator'], 'Prefer the new names in this module' )
