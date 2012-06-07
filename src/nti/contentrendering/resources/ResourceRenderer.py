#!/usr/bin/env python

from __future__ import print_function, unicode_literals

import os

from plasTeX.Renderers import Renderable as BaseRenderable
from plasTeX.Renderers import Renderer as BaseRenderer
from plasTeX.Renderers import mixin, unmix
from plasTeX.DOM import Node
from plasTeX.Logging import getLogger
from plasTeX.Filenames import Filenames


import zope.dottedname.resolve as dottedname

from . import RESOURCE_TYPES

logger = getLogger( __name__ )

def createResourceRenderer(baserenderername, resourcedb):
	"""
	Returns a new plasTeX Renderer object that will use the given resource database
	to locate images, vector images, and any uses of the ``resource`` property in templates.

	"""
	# Load renderer
	factory = dottedname.resolve( 'plasTeX.Renderers.%s.Renderer' % baserenderername )

	# We want to replace the BaseRenderer's render method, but we still need the subclasses
	# to do their work before they call through to the super class, so we cannot simply
	# replace the render method on the instance.
	# Instead, we dynamically derive a new class and insert it into the Method-Resolution-Order
	# (inheritance tree) just /before/ BaseRender. Our implementation will not call super, and so
	# we effectively replace BaseRendere. NOTE: This depends on cooperative subclasses that /do/ call
	# super

	bases = list( factory.__mro__ )
	bases.insert( bases.index( BaseRenderer ), _ResourceRenderer )

	factory = type( str('_%sResourceRenderer' % baserenderername), tuple(bases), {} )


	renderer = factory()
	renderer.renderableClass = Renderable
	renderer.resourcedb = resourcedb

	return renderer

def renderDocument(self, document, postProcess=None):
	"""
	Invoke the rendering process

	This method invokes the rendering process as well as handling
	the setup and shutdown of image processing.

	Required Arguments:
	document -- the document object to render
	postProcess -- a function that will be called with the content of

	"""

	config = document.config

	# If there are no keys, print a warning.
	# This is most likely a problem.
	if not self.keys():
		logger.warning('There are no keys in the renderer. All objects will use the default rendering method.')

	# Mix in required methods and members
	mixin(Node, self.renderableClass)
	Node.renderer = self
	try:
		# Create a filename generator
		self.newFilename = Filenames(config['files'].get('filename', raw=True),
									 (config['files']['bad-chars'],
									  config['files']['bad-chars-sub']),
									 {'jobname':document.userdata.get('jobname', '')}, self.fileExtension)

		self.cacheFilenames(document)



		# Invoke the rendering process
		if self.renderMethod:
			getattr(document, self.renderMethod)()
		else:
			unicode(document)


		# Run any cleanup activities
		self.cleanup(document, self.files.values(), postProcess=postProcess)

		# Write out auxilliary information
		pauxname = os.path.join(document.userdata.get('working-dir','.'),
								'%s.paux' % document.userdata.get('jobname',''))
		rname = config['general']['renderer']
		document.context.persist(pauxname, rname)
	finally:
		# Remove mixins
		del Node.renderer
		unmix(Node, self.renderableClass)

class _ResourceRenderer(object):
	render = renderDocument

class Renderable(BaseRenderable):

	@property
	def image(self):
		return self.getResource(['png', 'orig', 1])

	@property
	def vectorImage(self):
		return self.getResource(['svg'])


	def contents(self, criteria):
		return self.renderer.resourcedb.getResourceContent(self.source, criteria)


	@property
	def resource(self):
		"""
		The resource property is an NTI extension for use in templates.
		It's value is the rendered unicode string for the first resource type in this
		object's `resourceTypes` attribute (preference list) that can be rendered (has a template).
		"""
		renderer = Node.renderer

		resourceTypes = getattr(self, 'resourceTypes', None)

		if not resourceTypes:
			logger.warning('No resource types for %s using default renderer %s', self.nodeName, renderer.default )
			return renderer.default(self)

		template = None

		for resourceType in resourceTypes:

			if not resourceType in RESOURCE_TYPES:
				continue

			resourceTemplateName = RESOURCE_TYPES[resourceType]
			resourceTemplateNameForNode = '%s_%s' % (resourceTemplateName, self.nodeName)

			template = renderer.find([resourceTemplateNameForNode, resourceTemplateName], None)

			if template is not None:
				break

		if template is None:
			logger.warning('Unable to find template from resourcetypes %s for node %s', resourceTypes, self.nodeName )
			return renderer.default(self)

		val = template(self)

		#From Renderer.unicode
		# If a plain string is returned, we have no idea what
		# the encoding is, but we'll make a guess.
		if type(val) is not unicode:
			logger.warning('The renderer for %s returned a non-unicode string.	 Using the default input encoding.', type(child).__name__)
			val = unicode(val, self.config['files']['input-encoding'])

		return val

	def getResource(self, criteria):
		return Node.renderer.resourcedb.getResource(self.source, criteria)
