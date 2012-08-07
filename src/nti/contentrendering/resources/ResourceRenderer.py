#!/usr/bin/env python

from __future__ import print_function, unicode_literals

import os

from plasTeX.Renderers import Renderable as BaseRenderable
from plasTeX.Renderers import Renderer as BaseRenderer
from plasTeX.Renderers import mixin, unmix, renderable_as_unicode
from plasTeX.DOM import Node
from plasTeX.Logging import getLogger
from plasTeX.Filenames import Filenames


import zope.dottedname.resolve as dottedname
from . import interfaces

logger = getLogger( __name__ )

def createResourceRenderer(baserenderername, resourcedb, unmix=True):
	"""
	Returns a new plasTeX Renderer object that will use the given resource database
	to locate images, vector images, and any uses of the ``resource`` property in templates.

	:param bool unmix: Rendering depends on mixing in various properties to the plasTeX DOM
		Node class so that all elements in the DOM have them, including the current renderer.
		If this is True (the default) then the rendering process will clean up this mixing
		before returning from :meth:`_ResourceRenderer.render`. If ``False``, then the mixins
		will be left; this is suitable only for one-off, single process applications (the entire
		mixing thing is suitable only for one-off processes.)

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

	# We also override the template registration method to capture templates
	# that are registered for rendering a particular type of resource. These
	# templates should not have names that actually appear in the document.
	# There can be multiple templates to create a particular type; they will be looked up
	# using the name of the node (for customization) followed by the template name itself.
	# The most recent template wins.
	def _setTemplate(self, template, options, filename=None):
		result = super(factory,self).setTemplate( template, options, filename=filename )
		if result and 'nti_resource_for' in options:
			# Register the name of this template for its resource representation
			self.template_names_by_type.setdefault( options['nti_resource_for'], [] ).insert( 0, options['name'] )

		return result

	factory.setTemplate = _setTemplate
	renderer = factory()
	renderer.renderableClass = Renderable
	renderer.resourcedb = resourcedb
	if not unmix:
		renderer.unmix_after_render = unmix

	return renderer

class _EnabledMockImager(object):
	"""
	An object with the 'enabled' property.

	This is useful to support expressions in existing TAL templates
	such as ``not self/renderer/vectorImager/enabled``. Our renderers
	are always enabled.
	"""

	enabled = True

class _ResourceRenderer(object):

	unmix_after_render = True

	def __init__( self, *args, **kwargs ):
		super(_ResourceRenderer,self).__init__( *args, **kwargs )
		self.template_names_by_type = {}

	def render(self, document, postProcess=None):
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
			logger.warning('There are no keys in the renderer. All objects will use the default rendering method.') # pragma: no cover

		# Mix in required methods and members
		document.renderer = self
		# FIXME: this is not thread safe
		mixin(Node, self.renderableClass)
		try:
			# Create a filename generator
			self.newFilename = Filenames(config['files'].get('filename', raw=True),
										 (config['files']['bad-chars'],
										  config['files']['bad-chars-sub']),
										 {'jobname':document.userdata.get('jobname', '')}, self.fileExtension)

			self.cacheFilenames(document)

			logger.info( "Using ResourceDB for images; imagers always enabled" ) # TODO: Should that be config?
			# note that these must be instance attributes because we come after BaseRenderer,
			# which sets them as instance attributes of None at __init__ time (so we can't set them in our __init__ either)
			self.vectorImager = _EnabledMockImager
			self.imager = _EnabledMockImager

			# Invoke the rendering process
			# Nothing uses the 'renderMethod' key:
			#if self.renderMethod:
			#	getattr(document, self.renderMethod)()
			assert not self.renderMethod

			unicode(document) # relies on side-effects to write the document to files

			# Run any cleanup activities
			self.cleanup(document, self.files.values(), postProcess=postProcess)

			# Write out auxilliary information
			pauxname = os.path.join(document.userdata.get('working-dir','.'),
									'%s.paux' % document.userdata.get('jobname',''))
			rname = config['general']['renderer']
			document.context.persist(pauxname, rname)
		finally:
			if self.unmix_after_render:
				# Remove mixins
				del document.renderer
				unmix(Node, self.renderableClass)



class Renderable(BaseRenderable):

	def __unicode__( self ):
		"""
		Like the superclass, but calls methods before and after rendering,
		and caches the rendered value.
		"""
		# The mixin process won't overwrite these things if they already exist
		cached_value = getattr( self, '_cached_unicode_tuple', (None,None) )
		if cached_value[0] == self.renderer:
			return cached_value[1]

		self._before_render()
		__traceback_info__ = self, type(self)
		result = renderable_as_unicode( self )
		after_result = self._after_render( result )
		if after_result is not None:
			result = after_result

		setattr( self, '_cached_unicode_tuple', (self.renderer, result) )
		return result

	def _before_render(self):
		pass
	def _after_render( self, rendered_unicode ):
		"""
		If you return from this method, it should be the value to use instead of
		`rendered_unicode`.
		If you fail to return (or return None), then `rendered_unicode` will be the result.
		"""
		return rendered_unicode

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
		renderer = self.renderer


		resourceTypes = interfaces.IRepresentationPreferences( self ).resourceTypes # getattr(self, 'resourceTypes', None)
		# If something asks for a resource, it better have a defined resourceType
		assert resourceTypes

		#if not resourceTypes:
		#	logger.warning('No resource types for %s using default renderer %s', self.nodeName, renderer.default )
		#	return renderer.default(self)

		template = None

		for resourceType in resourceTypes:

			template_names_registered_for_resource_type = renderer.template_names_by_type.get( resourceType, [] )
			template_names_for_node = ['%s_%s' % (x, self.nodeName) for x in template_names_registered_for_resource_type]

			template = renderer.find( template_names_for_node + template_names_registered_for_resource_type, None )

			if template is not None:
				break

		# Resources better be able to find a template. There's
		# no good defaults for these things.
		assert template is not None
		#if template is None:
		#	logger.warning('Unable to find template from resourcetypes %s for node %s', resourceTypes, self.nodeName )
		#	return renderer.default(self)

		val = template(self)

		#From Renderer.unicode
		# If a plain string is returned, we have no idea what
		# the encoding is, but we'll make a guess.
		if type(val) is not unicode: # pragma: no cover
			logger.warning('The renderer for %s returned a non-unicode string.	 Using the default input encoding.', type(child).__name__)
			val = unicode(val, self.config['files']['input-encoding'])

		return val

	def getResource(self, criteria):
		return self.renderer.resourcedb.getResource(self.source, criteria)
