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
from zope import component
import zope.dottedname.resolve as dottedname

try:
	import cPickle as mPickle
except ImportError:
	import pickle as mPickle



from collections import defaultdict

from .resourcetypeoverrides import ResourceTypeOverrides, normalize_source
from .contentunitrepresentations import ContentUnitRepresentations
from ._util import digester, copy
from . import interfaces

class ResourceDB(object):
	"""
	Manages external resources (images, mathml, videos, etc..) for a document
	"""

	dirty = False

	def __init__(self, document, path='resources', overridesLocation=None):
		"""
		:param document: A plasTeX document we will manage resources for.
		:param string path: The path into which to store the resource files. Defaults
			to the relative path "resources". We will create a directory based on the
			job name within this directory.
		:param string overridesLocation: If not None, the path to a directory of
			resource type overrides. See :class:`ResourceTypeOverrides`.
		"""
		self._document = document
		self._config = self._document.config
		self.overrides = ResourceTypeOverrides(overridesLocation, fail_silent=False) if overridesLocation is not None else {}

		if not path:
			path = 'resources'

		self._dbpath = os.path.join(path, self._document.userdata['jobname'])
		self.baseURL = self._dbpath
		if not os.path.isdir(self._dbpath):
			os.makedirs(self._dbpath)

		logger.info('Using %s as resource db', self._dbpath)

		self._indexPath = os.path.join(self._dbpath, 'resources.index')

		self._db = {} # TODO: We should be normalizing the source here just like overrides do?

		self._loadResourceDB()

	def __str__(self):
		return str(self._db)

	def generateResourceSets(self):

		# Generate a mapping of representation names to nodes  {'png': {node1, node2}, 'mathml': {node3, node4}}
		rep_names_to_nodes = defaultdict(set)

		for node in self._locate_representable_nodes(self._document):
			rep_prefs = interfaces.IRepresentationPreferences( node )
			for rType in rep_prefs.resourceTypes:
				# We don't want to regenerate an existing representation for
				# this same source
				representations = self._db.get( node.source )
				if representations is None or not representations.has_representation_of_type( rType ):
					rep_names_to_nodes[rType].add(node)

		for rType, nodes in rep_names_to_nodes.items():
			self._create_representations(rType, nodes)

		self.saveResourceDB()

	def _create_representations(self, resourceType, nodes):
		# Load a resource generate
		generator = self._loadGenerator(resourceType)
		new_representations = generator.process_batch( nodes )
		for new_representation in new_representations:
			keys = (resourceType,) + tuple(new_representation.qualifiers)
			self.setResource(new_representation.source, keys, new_representation)

	def _loadGenerator(self, resourceType):
		return component.getAdapter( self._document,
									 interfaces.IContentUnitRepresentationBatchConverter,
									 name=resourceType )


	def _locate_representable_nodes(self, node, _accum=None):
		"""
		Starting with a root node, locate and return and return all nodes within it (whether child or attribute)
		that have a preference about how they are represented as resources, taking into
		account any registered overrides.

		:return: A set of nodes that can be adapted to :class:`interfaces.IRepresentationPreferences`
		"""

		if _accum is None:
			# Shared recursive accumulator for efficiency.
			_accum = set()


		# Do we have any overrides?
		source = normalize_source( node.source )
		if source in self.overrides:
			logger.info( 'Applying resourceType override to %s', node )
			node.resourceTypes = self.overrides[source]
			interface.alsoProvides( node, interfaces.IRepresentationPreferences )

		# If the node has specific preferences, then
		if interfaces.IRepresentationPreferences( node, None ) is not None:
			_accum.add(node)


		for attrval in (getattr( node, 'attributes', None) or {}).values():
			for child in getattr( attrval, 'childNodes', () ):
				self._locate_representable_nodes(child, _accum)

		for child in node.childNodes:
			self._locate_representable_nodes(child, _accum)

		return _accum


	def _loadResourceDB(self, filename=None):
		"""
		Loads resources from an external file. The external file is loaded as a pickle
		and must be iterable with the `items` method. If the `path` of each item exists,
		it is inserted into the current object's database.
		"""
		if filename is None: filename = self._indexPath
		if os.path.isfile(filename):
			try:
				ext_db = mPickle.load(open(filename, 'rb'))

				for key, value in ext_db.items():
					if os.path.exists(os.path.join(self._dbpath, value.path)):
						self._db[key] = value
			except (ImportError, mPickle.PickleError):
				logger.exception( 'Error loading cache %s. Starting from scratch', filename )


	def setResource(self, source, keys, resource):

		self.dirty = True

		if not source in self._db:
			self._db[source] = ContentUnitRepresentations(source)

		resourceSet = self._db[source]

		resourceSet.setResource(self._storeResource(resourceSet, keys, resource), keys)


	def _storeResource(self, rs, keys, origResource):
		resource = _clone(origResource)

		digest = digester.digestKeys(keys)
		name = '%s%s' % (digest, os.path.splitext(resource.path)[1])

		relativeToDB = os.path.join(rs.path, name)

		newpath = os.path.join(self._dbpath, relativeToDB)
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
		if not os.path.isdir(os.path.dirname(self._indexPath)):
			os.makedirs(os.path.dirname(self._indexPath))

		if not self.dirty:
			return

		mPickle.dump(self._db, open(self._indexPath,'wb'))

	def _getResourceSet(self, source):
		if source in self._db:
			return self._db[source]

	def hasResource(self, source, keys):
		rsrcSet = self._getResourceSet(source)

		if not rsrcSet:
			return None

		return rsrcSet.hasResource(keys)

	def getResourceContent(self, source, keys):
		path = self.getResourcePath(source, keys)
		if path:
			with codecs.open(path, 'r', 'utf-8') as f:
				return f.read()


	def getResource(self, source, keys):

		rsrcSet = self._db.get(source)

		if rsrcSet == None:
			return None
		assert source == rsrcSet.source
		return rsrcSet.resources[digester.digestKeys(keys)]

	def getResourcePath(self, source, keys):
		rsrcSet = self._getResourceSet(source)

		if not rsrcSet:
			return None


		digest = digester.digestKeys(keys)
		resourcePath = os.path.join(self._dbpath, rsrcSet.path)

		for name in os.listdir(resourcePath):
			if name.startswith(digest):
				path = os.path.join(resourcePath, name)
				return path
