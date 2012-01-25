#!/usr/bin/env python2.7

import codecs, os
import resources
import tempfile
import subprocess
import cgi
import html2mathml
import warnings
_debug = False

from pkg_resources import resource_exists, resource_filename
def _require_resource_filename( mathjaxconfigname ):
	if not resource_exists( __name__, 'zpts/Themes/AoPS/js/' + mathjaxconfigname ):
		raise Exception( "Unable to get mathjax config" )
	warnings.warn( "MathJax config file has dependency on AoPS path" )
	return resource_filename( __name__, 'zpts/Themes/AoPS/js/' + mathjaxconfigname )

class ResourceSetGenerator(resources.BaseResourceSetGenerator):

	htmlfile 			= 'math.html'
	mathjaxconfigname	= 'mathjaxconfig.js'
	# FIXME: This path assumption is not good.
	# we should be at least using the jobname?
	mathjaxconfigfile	= _require_resource_filename(mathjaxconfigname)

	wrapInText = False

	def __init__(self, compiler, encoding, batch):
		super(ResourceSetGenerator, self).__init__(compiler, encoding, batch)

		# TODO: Why the check???
		self.configName = self.mathjaxconfigfile if self.mathjaxconfigname else None
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
		<script type="text/javascript" src="http://cdn.mathjax.org/mathjax/latest/MathJax.js?config=TeX-AMS-MML_HTMLorMML"></script>')

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

		#We need to copy the html file
		htmlOutFile = os.path.join(tempdir, self.htmlfile)
		codecs.open(htmlOutFile, 'w', 'utf-8').write(htmlSource)

		configName = os.path.basename(self.mathjaxconfigfile)
		configOutFile = os.path.join(tempdir, configName)
		try:
			configOutFile = os.path.join(tempdir, configName)
			resources.copy(self.mathjaxconfigfile, configOutFile, _debug)

			program	 = self.compiler
			command = '%s "%s"' % (program, htmlOutFile)

			stdout, stderr = subprocess.Popen( command, shell=True, stdout=subprocess.PIPE).communicate()

			if _debug:
				print 'out'
				print stdout
				print 'error'
				print stderr

			return (stdout, tempdir)
		finally:
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
	javascript = os.path.join( os.path.dirname(__file__), 'js', 'tex2html.js' )

	def __init__(self, document):
		super(ResourceGenerator, self).__init__(document)
		warnings.warn( "Using phantomjs from PATH" )
		self.compiler = 'phantomjs %s' % (self.javascript)
		if not os.path.exists( self.javascript ):
			raise Exception( "Unable to get javascript %s" % self.javascript )

	def createResourceSetGenerator(self, compiler='', encoding='utf-8', batch=0):
		return ResourceSetGenerator(compiler, encoding, batch)


def _processBatchSource(generator, params):
	if generator.size() > 0:
		return generator.processSource()

	return ()


