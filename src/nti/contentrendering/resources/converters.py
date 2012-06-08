#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Base classes and useful functionality for implementing :class:`interfaces.IContentUnitRepresentationBatchConverter`
objects.

$Id$
"""
from __future__ import print_function, unicode_literals

import os
import subprocess
import time
from StringIO import StringIO
import codecs
import tempfile

from zope import interface

from plasTeX.Imagers import WorkingFile
from plasTeX.Filenames import Filenames

from . import interfaces

_marker = object()
logger = __import__('logging').getLogger(__name__)

@interface.implementer(interfaces.IContentUnitRepresentationBatchConverter)
class AbstractContentUnitRepresentationBatchConverter(object):
	"""
	Implements batch conversion of resources by acting as a wrapper
	to drive an object that can compile and transform a batch of resources at once.
	"""

	_final_methods = ('storeKeys','createResourceSetGenerator',
					   'generateResources', 'storeResources', 'canGenerate')


	def __init__(self, document):
		self.document = document
		self.batch_args = ()
		self.batch_kwargs = {}
		for final in self._final_methods:
			if getattr( self, final ) is not getattr( AbstractContentUnitRepresentationBatchConverter, final ):
				raise ValueError( "Cannot override deprecated method %s" % final ) #pragma: no cover


	def _new_batch_converter_driver(self, *args, **kwargs):
		raise NotImplementedError # pragma: no cover

	def process_batch( self, content_units ):

		generatableSources = [s.source for s in content_units]

		size = len(generatableSources)
		if not size > 0:
			return ()

		return self._new_batch_converter_driver( *self.batch_args, **self.batch_kwargs ).convert_batch( generatableSources )



@interface.implementer(interfaces.IContentUnitRepresentationBatchCompilingConverter)
class AbstractCompilingContentUnitRepresentationBatchConverter(AbstractContentUnitRepresentationBatchConverter):
	"""
	Implements batch conversion of resources by acting as a wrapper
	to drive an object that can compile and transform a batch of resources at once.
	"""

	compiler = ''
	debug = False

	def _new_batch_converter_driver(self, *args, **kwargs ):
		return self

	def _new_batch_compile_driver( self, document, *args, **kwargs ):
		raise NotImplementedError  # pragma: no cover

	def convert_batch( self, generatableSources ):
		encoding = self.document.config['files']['input-encoding']
		generator = self._new_batch_compile_driver( self.document, compiler=self.compiler, encoding=encoding)
		generator.writePreamble()
		for s in generatableSources:
			generator.addResource(s)
		generator.writePostamble()

		return generator.compile_batch_to_representations()



for _x in AbstractContentUnitRepresentationBatchConverter._final_methods:
	setattr( AbstractContentUnitRepresentationBatchConverter, _x, _marker )

class AbstractDocumentCompilerDriver(object):
	"""
	Accumulates resources into a single document which is compiled as a file;
	the compiler is expected to produce output files is that same directory.
	"""

	document_filename = 'resources'
	document_extension = 'tex'
	compiler = None

	def __init__(self, document, compiler='', encoding='utf-8', batch=0, **kwargs):
		self.document = document
		self.batch = batch
		self.writer = StringIO()
		if compiler:
			self.compiler = compiler
		self.encoding = encoding
		self.generatables = list()

	def size(self):
		return len(self.generatables)

	def writePreamble(self):
		pass

	def writePostamble(self):
		pass

	def addResource(self, s):
		self.generatables.append(s)
		self.writeResource(s)

	def writeResource(self, source):
		pass

	def compile_batch_to_representations(self):

		start = time.time()

		workdir = self.compileSource()

		resources = self.create_resources_from_compiled_directory(workdir)
		nresources = len(resources)

		if nresources != len(self.generatables):
			logger.warn( 'Expected %s files but only generated %s for batch %s',
						 len(self.generatables), nresources, self.batch )

		elapsed = time.time() - start
		logger.info( "%s resources generated in %sms for batch %s", nresources, elapsed, self.batch )

		return resources

	def _run_compiler_on_file( self, filename ):
		"""
		:return: The exit status of the command.
		:raise subprocess.CalledProcessError: If the command fails
		"""
		# Run the compiler
		os.environ['SHELL'] = '/bin/sh'
		program = self.compiler
		# XXX This is fairly dangerous!
		#return os.system(r"%s %s" % (program, filename))
		return subprocess.check_call( (program, filename) )
		#JAM: This does not work. Fails to read input
		# cmd = str('%s %s' % (program, filename))
		# print shlex.split(cmd)
		# p = subprocess.Popen(shlex.split(cmd),
		# 			 stdout=subprocess.PIPE,
		# 			 stderr=subprocess.STDOUT,
		# 			 )
		# while True:
		# 	line = p.stdout.readline()
		# 	done = p.poll()
		# 	if line:
		# 		imagelogger.info(str(line.strip()))
		# 	elif done is not None:
		# 		break



	def compileSource(self):
		"""
		Writes the accumulated document to a file in a temporary directory, and then
		runs the compiler.
		:return: The name of the temporary directory.
		"""

		# Make a temporary directory to work in
		tempdir = tempfile.mkdtemp()

		filename = os.path.join(tempdir, self.document_filename + '.' + self.document_extension )

		self.source().seek(0)
		with codecs.open(filename,'w',self.encoding ) as out:
			out.write(self.source().read())

		self._run_compiler_on_file( filename )

		return tempdir


	def create_resources_from_compiled_directory(self, workdir):
		"""
		Given the directory in which the document was compiled,
		collect and return the generated resources.
		"""
		raise NotImplementedError( "Creating resources from compiled directory" ) #pragma: no cover

	def source(self):
		return self.writer

	def write(self, data):
		if data:
			self.writer.write(data)

class AbstractOneOutputDocumentCompilerDriver(AbstractDocumentCompilerDriver):
	"""
	Assumes the compiler creates one output document, looks for, and converts that.

	The output document is looked for based on the compiler document filename
	plus any one of the `output_extensions`.
	"""

	output_extensions = ('dvi','pdf','ps','xml') # The defaults are setup for tex

	def create_resources_from_compiled_directory(self, tempdir):

		output = None
		for ext in self.output_extensions:
			fname = self.document_filename + '.' + ext
			fpath = os.path.join(tempdir, fname)
			if os.path.isfile(fpath):
				output = WorkingFile(fpath, 'rb', tempdir=tempdir)
				break

		if output is None: #pragma: no cover
			__traceback_info__ = (self, tempdir, self.output_extensions)
			raise ValueError( "Compiler did not produce any output" )

		return self.convert(output, tempdir)

	def convert(self, output, workdir):
		"""
		Convert output to resources.
		:param output: An open file. When this file is closed, the temp directory will be deleted.
		:param workdir: The directory used by the compiler.
		:return: A sequence of content representation objects (resources).
		"""
		__traceback_info__ = self
		raise NotImplementedError # pragma: no cover

class AbstractLatexCompilerDriver(AbstractOneOutputDocumentCompilerDriver):
	"""
	Drives a compiler that takes latex input.
	"""

	def writePreamble(self):
		self.write('\\scrollmode\n')
		self.write(self.document.preamble.source)
		self.write('\\makeatletter\\oddsidemargin -0.25in\\evensidemargin -0.25in\n')
		self.write('\\begin{document}\n')

	def writePostamble(self):
		self.write('\n\\end{document}\\endinput')

	def writeResource(self, source):
		self.write('%s\n%s\n' % ('', source))

class ImagerContentUnitRepresentationBatchConverterDriver(object):

	def __init__(self, imager):
		self.imager = imager

	def convert_batch(self, generatables):
		images = []
		for source in generatables:
			#TODO newImage completely ignores the concept of imageoverrides
			images.append(self.imager.newImage(source))

		self.imager.close()

		return images


class ImagerContentUnitRepresentationBatchConverter(AbstractContentUnitRepresentationBatchConverter):

	concurrency = 1
	imagerClass = None

	def __init__(self, document, imagerClass):
		super(ImagerContentUnitRepresentationBatchConverter, self).__init__(document)

		self.imagerClass = imagerClass
		if getattr(self.imagerClass,'resourceType', None):
			self.resourceType = self.imagerClass.resourceType
		else:
			self.resourceType = self.imagerClass.fileExtension[1:]

	def _new_batch_converter_driver(self, *args, **kwargs ):
		return ImagerContentUnitRepresentationBatchConverterDriver(self.createImager())

	def createImager(self):
		newImager = self.imagerClass(self.document)

		# create a tempdir for the imager to write images to
		tempdir = tempfile.mkdtemp()
		newImager.newFilename = Filenames(os.path.join(tempdir, 'img-$num(12)'),
										  extension=newImager.fileExtension)

		newImager._filecache = os.path.join(os.path.join(tempdir, '.cache'),
											newImager.__class__.__name__+'.images')

		return newImager
