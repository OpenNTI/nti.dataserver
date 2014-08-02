#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

import os

from hamcrest import assert_that
from hamcrest import is_
from hamcrest import contains
from hamcrest import has_length
from hamcrest import has_property
from hamcrest import close_to


from nti.contentrendering.tests import simpleLatexDocumentText
from nti.contentrendering.tests import ContentrenderingLayerTest
from nti.contentrendering.tests import buildDomFromString


from nti.contentrendering.resources import interfaces
from nti.contentrendering.resources.converters import ImagerContentUnitRepresentationBatchConverter
from nti.contentrendering.resources.converters import AbstractLatexCompilerDriver
from nti.contentrendering.resources.converters import AbstractCompilingContentUnitRepresentationBatchConverter

from nti.testing.matchers import verifiably_provides

class TestImagerContentUnitRepresentationBatchConverter(ContentrenderingLayerTest):


	def test_generator(self):
		class Image(object):
			path = 'path'
		class Imager(object):
			fileExtension = '.png'
			def __init__( self, document ):
				pass
			def getImage( self, node ):
				return Image()
			def newImage( self, source ):
				return Image()
			def close(self): pass


		converter = ImagerContentUnitRepresentationBatchConverter( buildDomFromString( simpleLatexDocumentText( '' ) ), Imager )
		assert_that( converter, verifiably_provides( interfaces.IContentUnitRepresentationBatchConverter ) )

		class ContentUnit(object):
			source = "abc"

		assert_that( converter.process_batch( [ContentUnit] ), contains( verifiably_provides( interfaces.IFilesystemContentUnitRepresentation ) ) )
		assert_that( converter.process_batch( [] ), is_( () ) )


class TestAbstractLatexCompiler(ContentrenderingLayerTest):

	def test_generator(self):
		class Driver(AbstractLatexCompilerDriver):
			compiler = 'true'

			def create_resources_from_compiled_directory(self, tempdir):
				# Fake it
				with open( os.path.join( tempdir, self.document_filename + '.xml'), 'w' ) as f:
					f.write( "<doc />" )

				return super(Driver,self).create_resources_from_compiled_directory( tempdir )

			def convert( self, output, tempdir ):
				return (ContentUnit.source,)

		class Converter(AbstractCompilingContentUnitRepresentationBatchConverter):
			resourceType = 'png'
			def _new_batch_compile_driver(self, document, *args, **kwargs):
				return Driver(document)

		converter = Converter( buildDomFromString( simpleLatexDocumentText( '' ) ) )
		assert_that( converter, verifiably_provides( interfaces.IContentUnitRepresentationBatchCompilingConverter ) )

		class ContentUnit(object):
			source = "abc"

		assert_that( converter.process_batch( [ContentUnit] ), contains( ContentUnit.source ) )

from .. converter_svg import _do_convert, PDF2SVG
import unittest
import shutil
import tempfile

from .. import converter_svg

class TestSvgConverter(unittest.TestCase):

	input_filename = os.path.join(os.path.dirname(__file__), 'datastructure_comparison.pdf')

	def test_do_convert(self):
		tempdir = tempfile.mkdtemp()
		cwd = os.getcwd()
		os.chdir(tempdir)
		try:
			filename  = _do_convert( 1, self.input_filename )
		finally:
			os.chdir(cwd)
			shutil.rmtree( tempdir )

		assert_that( filename, is_('img1.svg'))

	def test_converter(self):
		tempdir = tempfile.mkdtemp()
		cwd = os.getcwd()
		os.chdir(tempdir)
		class Executor(object):
			def __init__(self, **kwargs):
				pass
			def map(self, *args):
				return map(*args)

			def __enter__(self):
				return self

			def __exit__(self, t, v, tb):
				return

		class Image(object):
			pass

		orig_exec = converter_svg.ProcessPoolExecutor
		converter_svg.ProcessPoolExecutor = Executor
		try:
			with open(self.input_filename, 'rb') as f:
				imager = PDF2SVG.__new__(PDF2SVG)
				imager.images = {'key' + str(i): Image() for i in range(24)}
				_, images = imager.executeConverter(f)

			assert_that( images, has_length(24) )
			assert_that( imager.images['key0'], has_property('width', close_to(640.0, 2.0)) )
		finally:
			converter_svg.ProcessPoolExecutor = orig_exec
			os.chdir(cwd)
			shutil.rmtree( tempdir )


from .. converter_html_wrapped import _HTMLWrapper, HTMLWrappedBatchConverterDriver
import codecs
from hamcrest import contains_string

class TestHTMLWrappedConverter(unittest.TestCase):
	in_file = os.path.join(os.path.dirname(__file__),u'__init__.py')
	ntiid = u'tag:nextthought.com,2011-10:NTI-HTML-UnitTests.html_wrapped_test'

	def test_HTMLWrapper(self):
		out_file = self.in_file + u'.html'

		util = _HTMLWrapper(self.ntiid, self.in_file, out_file)

		assert_that( util.filename, contains_string(out_file) )
		util.write_to_file()

		data = u''
		with codecs.open( out_file, 'rb', 'utf-8') as f:
			data = f.read()

		assert_that( data, contains_string(u'# -*- coding: utf-8 -*-'))
		assert_that( data, contains_string(util.data['last-modified']))
		assert_that( data, contains_string(util.data['title']))

		os.remove(out_file)

	def test_converter(self):
		class Dummy_Unit(object):
			attributes = {}
			source = u''
			ntiid = u''

		converter = HTMLWrappedBatchConverterDriver()
		try:
			unit = Dummy_Unit()
			unit.attributes['src'] = self.in_file
			unit.ntiid = self.ntiid

			values = converter._convert_unit(unit)

			data = u''
			with codecs.open( values[0].path, 'rb', 'utf-8') as f:
				data = f.read()
				assert_that( data, contains_string(u'# -*- coding: utf-8 -*-'))

			data = u''
			with codecs.open( values[1].path, 'rb', 'utf-8') as f:
				data = f.read()
				assert_that( data, contains_string(u'# -*- coding: utf-8 -*-'))
		finally:
			converter.close()
