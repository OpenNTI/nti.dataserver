#!/usr/bin/env python
import logging
logger = logging.getLogger(__name__)

from . import run_phantom_on_page
import codecs, os
import resources
import tempfile

import cgi
import html2mathml

_debug = False

from nti.contentrendering import javascript_path
from pkg_resources import resource_exists, resource_filename
def _require_resource_filename( mathjaxconfigname ):
	if not resource_exists( __name__, '/js/' + mathjaxconfigname ):
		raise Exception( "Unable to get default mathjax config" )
	return resource_filename( __name__, '/js/' + mathjaxconfigname )

def _find_theme_mathjaxconfig(name):
	"""
	Looks through the configured themes and returns the first mathjaxconfig found.

	Since we don't have a theme name (and no trivial way to get it) this relies
	on the fact that we put the job-local Templates directory, which should have
	one theme, first on the template path.
	"""
	for dirname in os.environ.get( 'XHTMLTEMPLATES', '' ).split( os.path.pathsep ):
		dirname = os.path.join( dirname, 'Themes' )
		if os.path.exists( dirname ):
			files = [os.path.join( dirname, x, 'js', name ) for x in os.listdir( dirname )]
			for f in files:
				if os.path.exists( f ):
					return f



class ResourceSetGenerator(resources.BaseResourceSetGenerator):

	htmlfile 			= 'math.html'
	mathjaxconfigname	= 'mathjaxconfig.js'
	# FIXME: This path assumption is not good.
	# we should be at least using the jobname?
	mathjaxconfigfile	= _require_resource_filename('defaultmathjaxconfig.js')

	wrapInText = False

	def __init__(self, compiler, encoding, batch):
		super(ResourceSetGenerator, self).__init__(compiler, encoding, batch)

		self.configName = _find_theme_mathjaxconfig( self.mathjaxconfigname )
		if not self.configName:
			print 'Mathjax config has not been provided.'
		elif not os.path.exists( self.configName ):
			raise Exception( "Config does not exist %s" % self.configName )


	def writePreamble(self, preamble):

		self.write('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"\
		"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">\
		<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">\
		<head>\
		<link rel="stylesheet" href="styles/styles.css" />\
		<script type="text/javascript" src="http://cdn.mathjax.org/mathjax/1.1-latest/MathJax.js?config=TeX-AMS-MML_HTMLorMML"></script>')

		self.write('<script type="text/javascript" src="%s"></script>' % self.mathjaxconfigfile)
		if self.configName:
			self.write('<script type="text/javascript" src="%s"></script>' % self.configName)

		self.write('<script type="text/javascript"\
		src="http://ajax.googleapis.com/ajax/libs/jquery/1.6.1/jquery.min.js"></script>\
		<script type="text/javascript" src="https://ajax.googleapis.com/ajax/libs/jqueryui/1.8.13/jquery-ui.min.js">\
		</script>\
		</head>\
		<body>')

	def writeResource(self, source, context):
		if self.wrapInText:
			self.write('Cras vel metus diam, sed molestie risus. Etiam mattis, nisi sed malesuada luctus, arcu purus euismod velit, \
			eu luctus felis nisi vitae nulla. Vestibulum euismod leo vel mauris commodo egestas. Nullam eu metus vitae velit euismod \
			eleifend ac vitae nibh.  consectetur commodo.\
			Nunc tincidunt, lacus sollicitudin vehicula ultricies, odio libero tempus magna, eget pretium nisi neque egestas est. \
			Nulla mattis, erat quis accumsan ultrices, mi neque feugiat tellus, sed fermentum elit lorem vel lacus. Pellentesque \
			in nunc dolor ')
		self.write('%s<span class="mathjax math tex2jax_process mathquill-embedded-latex">\(%s\)</span>' %\
					(context , cgi.escape(source[1:-1])))
		if self.wrapInText:
			self.write('. Cras vel metus diam, sed molestie risus. Etiam mattis, nisi sed malesuada luctus, arcu purus euismod velit, \
			eu luctus felis nisi vitae nulla. Vestibulum euismod leo vel mauris commodo egestas. Nullam eu metus vitae velit euismod \
			eleifend ac vitae nibh. Phasellus u diam. Suspendisse condimentum consectetur commodo.\
			Nunc tincidunt, lacus sollicitudin vehicula ultricies, odio libero tempus magna, eget pretium nisi neque egestas est. \
			Nulla mattis, erat quis accumsan ultrices, mi neque feugiat tellus, sed fermentum elit lorem vel lacus. Pellentesque \
			in nunc dolor ')

	def writePostamble(self):
		self.write('</body></html>')

	def compileSource(self):

		source = self.writer
		source.seek(0)
		htmlSource = source.read()

		tempdir = tempfile.mkdtemp()

		# We need to copy the html file
		htmlOutFile = os.path.join(tempdir, self.htmlfile)
		codecs.open(htmlOutFile, 'w', 'utf-8').write(htmlSource)

		copied_configs = []
		try:
			for i in (self.mathjaxconfigfile, self.configName):
				if not i: continue
				configName = os.path.basename(i)
				configOutFile = os.path.join(tempdir, configName)
				resources.copy(i, configOutFile, _debug)
				copied_configs.append( configOutFile )

			stdout = run_phantom_on_page( htmlOutFile, self.compiler, expect_non_json_output=True )

			return (stdout, tempdir)
		finally:
			for configOutFile in copied_configs:
				os.remove(configOutFile)

	def convert(self, output, workdir):

		tempdir = tempfile.mkdtemp()

		maths = [math.strip().decode('utf-8') for math in output.split('\n') if math.strip()]

		i = 1
		files = list()
		for math in maths:
			fname = os.path.join(tempdir, ('math_%s.xml' % i))
			codecs.open(fname, 'w', 'utf-8').write(math)
			files.append(fname)
			i = i+1

		return [resources.Resource(name) for name in files]


class ResourceGenerator(html2mathml.ResourceGenerator):

	concurrency = 4
	illegalCommands = None
	resourceType = 'mathjax_inline'
	javascript = javascript_path( 'tex2html.js' )

	def __init__(self, document):
		super(ResourceGenerator, self).__init__(document)
		self.compiler = self.javascript

	def createResourceSetGenerator(self, compiler='', encoding='utf-8', batch=0):
		return ResourceSetGenerator(compiler, encoding, batch)


def _processBatchSource(generator, params):
	if generator.size() > 0:
		return generator.processSource()

	return ()
