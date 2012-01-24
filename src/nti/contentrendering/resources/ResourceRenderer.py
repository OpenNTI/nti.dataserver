import os

from plasTeX.Renderers import Renderable as BaseRenderable
from plasTeX.Renderers import Renderer as BaseRenderer
from plasTeX.Renderers import mixin, unmix
from plasTeX.DOM import Node
from plasTeX.Logging import getLogger
from plasTeX.Filenames import Filenames
from . import RESOURCE_TYPES

logger = getLogger( __name__ )

def createResourceRenderer(baserenderername, resourcedb):
	# Load renderer
	try:
		_name = 'plasTeX.Renderers.%s' % baserenderername
		_module = __import__(_name, globals(), locals(), ['Renderer'], -1)
	except ImportError:
		logger.error('Could not import renderer "%s"' % baserenderername)
		raise

	# it would be nice to patch just the instance but PageTemplates render method
	# calls BaseRenderer.render method
	BaseRenderer.render = renderDocument
	BaseRenderer.renderableClass = Renderable
	renderer = _module.Renderer()
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
	mixin(Node, type(self).renderableClass)
	Node.renderer = self

	# Create a filename generator
	self.newFilename = Filenames(config['files'].get('filename', raw=True),
								 (config['files']['bad-chars'],
								  config['files']['bad-chars-sub']),
								 {'jobname':document.userdata.get('jobname', '')}, self.fileExtension)

	self.cacheFilenames(document)



	# Invoke the rendering process
	if type(self).renderMethod:
		getattr(document, type(self).renderMethod)()
	else:
		unicode(document)


	# Run any cleanup activities
	self.cleanup(document, self.files.values(), postProcess=postProcess)

	# Write out auxilliary information
	pauxname = os.path.join(document.userdata.get('working-dir','.'),
							'%s.paux' % document.userdata.get('jobname',''))
	rname = config['general']['renderer']
	document.context.persist(pauxname, rname)

	# Remove mixins
	del Node.renderer
	unmix(Node, type(self).renderableClass)

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
		renderer = Node.renderer

		resourceTypes = None
		if getattr(self, 'resourceTypes', None):
			resourceTypes = self.resourceTypes

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


