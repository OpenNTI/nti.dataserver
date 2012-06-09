#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals

logger = __import__( 'logging' ).getLogger(__name__)

import os,  codecs
from copy import deepcopy as _clone

from hashlib import sha1

from zope.deprecation import deprecated
from zope import interface
import zope.dottedname.resolve as dottedname

try:
	import cPickle as mPickle
except ImportError:
	import pickle as mPickle



from plasTeX.Imagers import  Image

from collections import defaultdict

from .resourcetypeoverrides import ResourceTypeOverrides
from .contentunitrepresentations import ContentUnitRepresentations
from ._util import digester, copy
from . import interfaces

class ResourceDB(object):
	"""
	Manages external resources (images, mathml, videos, etc..) for a document
	"""

	dirty = False

	types = {'mathjax_inline': 'nti.contentrendering.tex2html.ResourceGenerator',
			 'mathjax_display': 'nti.contentrendering.displaymath2html.ResourceGenerator',
			 'svg': 'nti.contentrendering.pdf2svg.ResourceGenerator',
			 'png': 'nti.contentrendering.gspdfpng2.ResourceGenerator',
			 'mathml': 'nti.contentrendering.html2mathml.ResourceGenerator'}


	def __init__(self, document, path=None, overridesLocation=None):
		self.__document = document
		self.__config = self.__document.config
		self.overrides = ResourceTypeOverrides(overridesLocation, fail_silent=False) if overridesLocation is not None else {}

		if not hasattr(Image, '_url'): # Not already patched
			Image._url = None
			def seturl(self, value):
				self._url = value

			def geturl(self):
				return self._url

			Image.url = property(geturl, seturl)

		if not path:
			path = 'resources'

		self.__dbpath = os.path.join(path, self.__document.userdata['jobname'])
		self.baseURL = self.__dbpath
		if not os.path.isdir(self.__dbpath):
			os.makedirs(self.__dbpath)

		logger.info('Using %s as resource db', self.__dbpath)

		self.__indexPath = os.path.join(self.__dbpath, 'resources.index')

		self.__db = {}

		self.__loadResourceDB()

	def __str__(self):
		return str(self.__db)

	def generateResourceSets(self):

		#set of all nodes we need to generate resources for
		nodesToGenerate = self.__findNodes(self.__document)

		#Generate a mapping of types to source  {png: {src2, src5}, mathml: {src1, src5}}
		typesToSource = defaultdict(set)

		for node in nodesToGenerate:

			for rType in node.resourceTypes:
				# We don't want to regenerate for source that already exists
				if not node.source in self.__db:
					typesToSource[rType].add(node.source)
				else:
					hasType = False
					for resource in self.__db[node.source].resources.values():
						resourceType = getattr(resource, 'resourceType', None)
						if resourceType == rType:
							hasType = True
							break
					if not hasType:
						typesToSource[rType].add(node.source)

		for rType, sources in typesToSource.items():
			self.__generateResources(rType, sources)

		self.saveResourceDB()

	def __generateResources(self, resourceType, sources):
		#Load a resource generate
		generator = self.__loadGenerator(resourceType)

		if not generator:
			logger.warn( "Not generating resource %s for %s", resourceType, sources )
			return

		generator.generateResources(sources, self)

	def __loadGenerator(self, resourceType):
		if not resourceType in self.types:
			logger.warn('No generator specified for resource type %s', resourceType)
			return None
		try:
			return dottedname.resolve( self.types[resourceType] )(self.__document)
		except ImportError, msg:
			logger.warning("Could not load custom imager '%s' because '%s'", resourceType, msg)
			return None

	def __findNodes(self, node):
		nodes = []

		#Do we have any overrides
		#FIXME Be smarter about this.  The source for mathnodes is reconstructed so the
		#whitespace is all jacked up.  The easiest (not safest) thing to do is strip whitespace
		source = ''.join(node.source.split())
		if source in self.overrides:
			logger.info( 'Applying resourceType override to %s', node )
			node.resourceTypes = self.overrides[source]
			interface.alsoProvides( node, interfaces.IRepresentationPreferences )

		if interfaces.IRepresentationPreferences( node, None ) is not None:
			nodes.append(node)

		if getattr(node, 'attributes', None):
			for attrval in node.attributes.values():
				if getattr(attrval, 'childNodes', None):
					for child in attrval.childNodes:
						nodes.extend(self.__findNodes(child))

		for child in node.childNodes:
			nodes.extend(self.__findNodes(child))

		return list(set(nodes))


	def __loadResourceDB(self, debug = True):
		if os.path.isfile(self.__indexPath):
			try:

				self.__db = mPickle.load(open(self.__indexPath, 'rb'))

				for key, value in self.__db.items():

					if not os.path.exists(os.path.join(self.__dbpath,value.path)):
						del self.__db[key]
						continue
			except ImportError:
				logger.exception( 'Error loading cache.  Starting from scratch' )
				os.remove(self.__indexPath)
				self.__db = {}
		else:
			self.__db = {}


	def setResource(self, source, keys, resource, debug = False):

		self.dirty = True

		if not source in self.__db:
			self.__db[source] = ContentUnitRepresentations(source)

		resourceSet = self.__db[source]

		resourceSet.setResource(self.__storeResource(resourceSet, keys, resource, debug), keys)


	def __storeResource(self, rs, keys, origResource, debug = False):
		resource = _clone(origResource)

		digest = digester.digestKeys(keys)
		name = '%s%s' % (digest, os.path.splitext(resource.path)[1])

		relativeToDB = os.path.join(rs.path, name)

		newpath = os.path.join(self.__dbpath, relativeToDB)
		copy(resource.path, newpath)
		resource.path = name
		resource.filename = name
		resource.resourceSet = rs
		resource.url = self.urlForResource(resource)


		return resource

	def urlForResource(self, resource):
		if self.baseURL and not self.baseURL.endswith('/'):
			self.baseURL = '%s/' % self.baseURL

		if not self.baseURL:
			self.baseURL = ''

		return '%s%s/%s' % (self.baseURL, resource.resourceSet.path, resource.path)

	def saveResourceDB(self):
		if not os.path.isdir(os.path.dirname(self.__indexPath)):
			os.makedirs(os.path.dirname(self.__indexPath))

		if not self.dirty:
			return

		mPickle.dump(self.__db, open(self.__indexPath,'wb'))

	def __getResourceSet(self, source):
		if source in self.__db:
			return self.__db[source]
		return None

	def hasResource(self, source, keys):
		rsrcSet = self.__getResourceSet(source)

		if not rsrcSet:
			return None

		return rsrcSet.hasResource(keys)

	def getResourceContent(self, source, keys):
		path = self.getResourcePath(source, keys)
		if path:
			with codecs.open(path, 'r', 'utf-8') as f:
				return f.read()
		return None

	def getResource(self, source, keys):

		rsrcSet = self.__db.get(source)

		if rsrcSet == None:
			return None
		assert source == rsrcSet.source
		return rsrcSet.resources[digester.digestKeys(keys)]

	def getResourcePath(self, source, keys):
		rsrcSet = self.__getResourceSet(source)

		if not rsrcSet:
			return None


		digest = digester.digestKeys(keys)
		resourcePath = os.path.join(self.__dbpath, rsrcSet.path)

		for name in os.listdir(resourcePath):
			if name.startswith(digest):
				path = os.path.join(resourcePath, name)
				return path

		return None
