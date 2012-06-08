#!/usr/bin/env python
"""
Defines objects for creating and querying on disk, in various forms, representations
of portions of a document (such as images and math expressions).

$Id$
"""

from __future__ import print_function, unicode_literals

import logging
logger = logging.getLogger(__name__)

import os, time, tempfile, shutil, codecs
import copy as cp

from hashlib import sha1

from zope.deprecation import deprecated
from UserDict import DictMixin

try:
	import cPickle as mPickle
except ImportError:
	import pickle as mPickle

from StringIO import StringIO
from plasTeX.Filenames import Filenames
from plasTeX.Imagers import WorkingFile

import zope.dottedname.resolve as dottedname

# try:
# 	import Image as PILImage
# 	import ImageChops as PILImageChops
# except ImportError:
# 	PILImage = PILImageChops = None

from zope import interface
from . import interfaces

from .resourcetypeoverrides import ResourceTypeOverrides #b/c export


def _set_default_resource_types():

	def _implement( cls, types ):
		interface.classImplements( cls,
								   interfaces.IRepresentableContentUnit,
								   interfaces.IRepresentationPreferences )
		cls.resourceTypes = types


	Arrays = dottedname.resolve( 'plasTeX.Base.Arrays' )

	tabularTypes = ('png', 'svg')
	_implement( Arrays.tabular, tabularTypes )
	_implement( Arrays.TabularStar, tabularTypes )
	_implement( Arrays.tabularx, tabularTypes )

	Math = dottedname.resolve( 'plasTeX.Base.Math' )

	#The math package does not correctly implement the sqrt macro.	It takes two args
	Math.sqrt.args = '[root]{arg}'

	inlineMathTypes = ('mathjax_inline', )
	displayMathTypes = ('mathjax_display', )

	#inlineMathTypes = ['mathjax_inline', 'png', 'svg']
	#displayMathTypes = ['mathjax_display', 'png', 'svg']
	_implement( Math.math, inlineMathTypes )
	_implement( Math.ensuremath, inlineMathTypes )

	_implement( Math.displaymath, displayMathTypes )
	_implement( Math.EqnarrayStar, displayMathTypes )
	# TODO: What about eqnarry?
	_implement( Math.equation, displayMathTypes )


	from plasTeX.Packages.graphicx import includegraphics
	_implement( includegraphics, ('png',) )

	from plasTeX.Packages import amsmath
	# TODO: Many of these are probably unnecessary as they share
	# common superclasses
	_implement( amsmath.align, displayMathTypes )
	_implement( amsmath.AlignStar, displayMathTypes )
	_implement( amsmath.alignat, displayMathTypes )
	_implement( amsmath.AlignatStar, displayMathTypes )
	_implement( amsmath.gather, displayMathTypes )
	_implement( amsmath.GatherStar, displayMathTypes )

	# XXX FIXME If we don't do this, then we can get
	# a module called graphicx reloaded from this package
	# which doesn't inherit our type. Who is doing that?
	import sys
	sys.modules['graphicx'] = sys.modules['plasTeX.Packages.graphicx']

# While import side-effects are usually bad, setting up the default
# resource types is required to make this package actually work, and
# is extremely unlikely to cause any conflicts or difficulty
_set_default_resource_types()

@interface.implementer(interfaces.IContentUnitRepresentation)
class Resource(object):

	def __init__(self, path=None, url=None, resourceSet=None, checksum=None):
		self.url = url
		self.path = path
		self.checksum = checksum
		self.resourceSet = resourceSet

	def __str__(self):
		return '%s' % self.path


from .contentunitrepresentations import ContentUnitRepresentations, ResourceRepresentations

ResourceSet = ResourceRepresentations
deprecated( 'ResourceSet', 'Prefer the name ResourceRepresentations')

from .ResourceDB import ResourceDB
deprecated( 'ResourceDB', 'Prefer the specific module' )

class BaseResourceSetGenerator(object):

	def __init__(self, compiler='', encoding = '', batch=0, **kwargs):
		self.batch = batch
		self.writer = StringIO()
		self.compiler = compiler
		self.encoding = encoding
		self.generatables = list()

	def size(self):
		return len(self.generatables)

	def writePreamble(self, preamble):
		self.write('\\scrollmode\n')
		self.write(preamble)
		self.write('\\makeatletter\\oddsidemargin -0.25in\\evensidemargin -0.25in\n')
		self.write('\\begin{document}\n')

	def writePostamble(self):
		self.write('\n\\end{document}\\endinput')

	def addResource(self, s, context=''):
		self.generatables.append(s)
		self.writeResource(s, context)

	def writeResource(self, source, context):
		self.write('%s\n%s\n' % (context, source))

	def processSource(self):

		start = time.time()

		(output, workdir) = self.compileSource()

		resources = self.convert(output, workdir)
		nresources = len(resources)

		if nresources != len(self.generatables):
			logger.warn( 'Expected %s files but only generated %s for batch %s',
						 len(self.generatables), nresources, self.batch )

		elapsed = time.time() - start
		logger.info( "%s resources generated in %sms for batch %s", nresources, elapsed, self.batch )

		return zip(self.generatables, resources)

	def compileSource(self):

		# Make a temporary directory to work in
		tempdir = tempfile.mkdtemp()

		filename = os.path.join(tempdir,'resources.tex')

		self.source().seek(0)
		with codecs.open(filename,
						 'w',
						 self.encoding ) as out:
			out.write(self.source().read())

		# Run LaTeX
		os.environ['SHELL'] = '/bin/sh'
		program = self.compiler

		os.system(r"%s %s" % (program, filename))

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

		output = None
		for ext in ['.dvi','.pdf','.ps','.xml']:
			fpath = os.path.join(tempdir,'resources' + ext)
			if os.path.isfile(fpath):
				output = WorkingFile('resources' + ext, 'rb', tempdir=tempdir)
				break

		return (output, tempdir)

	def convert(self, output, workdir):
		"""
		Convert output to resources
		"""
		return []

	def source(self):
		return self.writer

	def writer(self):
		return self.writer

	def write(self, data):
		if data:
			self.writer.write(data)

class BaseResourceGenerator(object):

	compiler = ''
	debug = False

	def __init__(self, document):
		self.document = document

	def storeKeys(self): #TODO: Rename. Is a 'representation description'
		return [self.resourceType]

	def context(self):
		return ''

	def createResourceSetGenerator(self, compiler='', encoding ='utf-8', batch = 0):
		return BaseResourceSetGenerator(self.document, compiler, encoding, batch)

	def generateResources(self, sources, db):

		generatableSources = [s for s in sources if self.canGenerate(s)]

		size = len(generatableSources)
		if not size > 0:
			return

		encoding = self.document.config['files']['input-encoding']
		generator = self.createResourceSetGenerator(self.compiler, encoding)
		generator.writePreamble(self.document.preamble.source)
		for s in generatableSources:
			generator.addResource(s, self.context())
		generator.writePostamble()

		self.storeResources(generator.processSource(), db, self.debug)

	def storeResources(self, tuples, db, debug=False):
		for source, resource in tuples:
			db.setResource(source, self.storeKeys(), resource)

	def canGenerate(self, source):
		return True

#End BaseResourceSetGenerator

class ImagerResourceSetGenerator(BaseResourceSetGenerator):

	def __init__(self, imager, batch=0):
		super(ImagerResourceSetGenerator, self).__init__('', '', batch)
		self.imager = imager

	def writePreamble(self, preamble):
		pass

	def writePostamble(self):
		pass

	def writeResource(self, source, context):
		pass

	def processSource(self):
		images = []
		for source in self.generatables:
			#TODO newImage completely ignores the concept of imageoverrides
			images.append(self.imager.newImage(source))

		self.imager.close()

		return zip(self.generatables, images)

	def compileSource(self):
		return (None, None)

	def convert(self, output, workdir):
		return []


#End ImagerResourceSetGenerator

class ImagerResourceGenerator(BaseResourceGenerator):

	concurrency = 1

	def __init__(self, document, imagerClass):
		super(ImagerResourceGenerator, self).__init__(document)

		self.imagerClass = imagerClass
		if getattr(self.imagerClass,'resourceType', None):
			self.resourceType = self.imagerClass.resourceType
		else:
			self.resourceType = self.imagerClass.fileExtension[1:]

	def createResourceSetGenerator(self, compiler='', encoding ='', batch = 0):
		return ImagerResourceSetGenerator(self.createImager(),  batch)

	def createImager(self):
		newImager = self.imagerClass(self.document)

		# create a tempdir for the imager to write images to
		tempdir = tempfile.mkdtemp()
		newImager.newFilename = Filenames(os.path.join(tempdir, 'img-$num(12)'),
										  extension=newImager.fileExtension)

		newImager._filecache = os.path.join(os.path.join(tempdir, '.cache'),
											newImager.__class__.__name__+'.images')

		return newImager

for name in ('BaseResourceSetGenerator', 'BaseResourceGenerator', 'ImagerResourceSetGenerator', 'ImagerResourceGenerator'):
	deprecated( name, 'Prefer the converters module.')

#End ImagerResourceGenerator
from ._util import copy

#End copy
