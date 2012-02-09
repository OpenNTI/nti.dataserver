#!/usr/bin/env python
import logging
logger = logging.getLogger( __name__ )

import codecs, os, re, sys
import resources
import xml.sax
from xml.sax.xmlreader import InputSource
from xml.dom import minidom
#from plasTeX.Imagers import *
from concurrent.futures import ProcessPoolExecutor

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

class ResourceSetGenerator(resources.BaseResourceSetGenerator):

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
			codecs.open(fpath,\
					 	'w',\
					 	self.encoding).write(mathml.toxml())
			resourceNames.append(resource)
			i = i + 1

		return [resources.Resource(os.path.join(workdir, name)) for name in resourceNames]

	def buildMathMLDOM(self, output):
		# Load up the results into a dom
		parser = xml.sax.make_parser()
		parser.setEntityResolver(MyEntityResolver())

		return minidom.parse(output, parser)

class ResourceGenerator(resources.BaseResourceGenerator):

	debug			= False

	concurrency		= 1
	compiler		= 'ttm'
	resourceType  	= _RESOURCE_TYPE
	illegalCommands	= [	'\\\\overleftrightarrow',\
					 	'\\\\vv',\
					 	'\\\\smash',\
					 	'\\\\rlin',\
					 	'\\\\textregistered']

	def createResourceSetGenerator(self, compiler='', encoding ='utf-8', batch = 0):
		return ResourceSetGenerator(self. compiler, encoding, batch)

	def generateResources(self, sources, db):

		generatableSources = [s for s in sources if self.canGenerate(s)]

		size = len(generatableSources)
		if not size > 0:
			logger.info( 'No sources to generate' )
			return

		logger.info( 'Generating %s sources', size )

		encoding = self.document.config['files']['output-encoding']
		generators = list()
		for i in range(self.concurrency):
			g = self.createResourceSetGenerator(self.compiler, encoding, i)
			generators.append(g)
			g.writePreamble(self.document.preamble.source)

		i = 0
		for s in generatableSources:
			g = generators[i]
			g.addResource(s, '')
			i = i+1 if (i+1) < self.concurrency else 0

		for g in generators:
			g.writePostamble()

		if self.concurrency > 1 and size > 1:
			# Process batches in parallel,
			params = [True] * self.concurrency
			with ProcessPoolExecutor() as executor:
				for tuples in executor.map(_processBatchSource, generators, params):
					self.storeResources(tuples, db, self.debug)
		else:
			g = generators[0]
			self.storeResources(g.processSource(), db, self.debug)

	def canGenerate(self, source):
		if not self.illegalCommands:
			return True

		for command in self.illegalCommands:
			if re.search(command, source):
				return False
		return True


def _processBatchSource(generator, params):
	if generator.size() > 0:
		return generator.processSource()

	return ()


