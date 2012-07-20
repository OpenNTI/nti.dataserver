#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals

logger = __import__('logging').getLogger(__name__)

from nti.contentrendering import run_phantom_on_page
import codecs, os

import tempfile

import cgi

from nti.contentrendering.resources import converters, _util
from nti.contentrendering.resources.contentunitrepresentations import FilesystemContentUnitRepresentation


from nti.contentrendering import javascript_path
from pkg_resources import resource_exists, resource_filename
def _require_resource_filename( mathjaxconfigname ):
	if not resource_exists( 'nti.contentrendering', '/js/' + mathjaxconfigname ): # pragma: no cover
		raise EnvironmentError( "Unable to get default mathjax config" )
	return resource_filename( 'nti.contentrendering', '/js/' + mathjaxconfigname )

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



class MathjaxInlineCompilerDriver(converters.AbstractOneOutputDocumentCompilerDriver):

	htmlfile 			= 'math.html'
	mathjaxconfigname	= 'mathjaxconfig.js'
	# FIXME: This path assumption is not good.
	# we should be at least using the jobname?
	mathjaxconfigfile	= _require_resource_filename('defaultmathjaxconfig.js')

	resourceType = None

	def __init__(self, document, compiler, encoding, batch):
		super(MathjaxInlineCompilerDriver, self).__init__(document, compiler, encoding, batch)

		self.configName = _find_theme_mathjaxconfig( self.mathjaxconfigname )
		if not os.path.exists( self.configName ): # pragma: no cover
			raise EnvironmentError( "Config does not exist %s" % self.configName )


	def writePreamble(self):

		self.write('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"\
		"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">\
		<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">\
		<head>\
		<link rel="stylesheet" href="styles/styles.css" />\
		<script type="text/javascript" src="http://cdn.mathjax.org/mathjax/1.1-latest/MathJax.js?config=TeX-AMS-MML_HTMLorMML"></script>')

		self.write('<script type="text/javascript" src="%s"></script>' % self.mathjaxconfigfile)
		self.write('<script type="text/javascript" src="%s"></script>' % self.configName)

		self.write('<script type="text/javascript"\
		src="http://ajax.googleapis.com/ajax/libs/jquery/1.6.1/jquery.min.js"></script>\
		<script type="text/javascript" src="https://ajax.googleapis.com/ajax/libs/jqueryui/1.8.13/jquery-ui.min.js">\
		</script>\
		</head>\
		<body>')

	def _compilation_source_for_content_unit( self, content_unit ):
		tex_without_delimiters = content_unit.source[1:-1]
		return '<span class="mathjax math tex2jax_process">\(%s\)</span>' % cgi.escape(tex_without_delimiters)

	def writePostamble(self):
		self.write('</body></html>')

	def compileSource(self):
		# TODO: A lot of this could be shared with the superclass
		source = self._writer
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
				_util.copy(i, configOutFile)
				copied_configs.append( configOutFile )

			stdout = run_phantom_on_page( htmlOutFile, self.compiler, expect_non_json_output=True )
			if stdout:
				stdout = stdout.decode( 'utf-8' ) # stdout comes in as bytes, make it unicode
			return stdout, tempdir
		finally:
			for configOutFile in copied_configs:
				os.remove(configOutFile)

	def create_resources_from_compiled_directory( self, arg ):
		"""
		Unlike the superclass, we actually expect a tuple of (output, workdir)
		which we pass directly to convert.
		"""
		return self.convert( *arg )

	def convert(self, output, workdir):

		tempdir = tempfile.mkdtemp()

		maths = [math.strip() for math in output.split('\n') if math.strip()]

		files = list()
		for i, math in enumerate(maths):
			fname = os.path.join(tempdir, ('math_%s.xml' % i))
			with codecs.open(fname, 'w', 'utf-8') as f:
				f.write(math)
			# Note this is slightly shady. We aren't keeping track of the original source anywhere
			# except for in the superclass, and the resource DB depends on us handing back the original
			# source. See superclass for more details
			files.append( FilesystemContentUnitRepresentation(path=fname, resourceType=self.resourceType, source=self._generatables[i]) )

		return files


class MathjaxInlineBatchConverter(converters.AbstractConcurrentConditionalCompilingContentUnitRepresentationBatchConverter):

	concurrency = 4
	illegalCommands = None
	resourceType = 'mathjax_inline'
	javascript = javascript_path( 'tex2html.js' )

	compiler_driver = MathjaxInlineCompilerDriver

	def __init__(self, document):
		super(MathjaxInlineBatchConverter, self).__init__(document)
		self.compiler = self.javascript

	def _new_batch_compile_driver(self, document, compiler='', encoding='utf-8', batch=0):
		result = self.compiler_driver(document, compiler, encoding, batch)
		result.resourceType = self.resourceType
		return result

ResourceSetGenerator = MathjaxInlineCompilerDriver
ResourceGenerator = MathjaxInlineBatchConverter


from zope.deprecation import deprecated
deprecated( ['ResourceGenerator','ResourceSetGenerator'], 'Prefer the new names in this module' )
