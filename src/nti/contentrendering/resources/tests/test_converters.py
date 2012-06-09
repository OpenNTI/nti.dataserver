#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals

import os

from hamcrest import assert_that, is_
from hamcrest import contains




import plasTeX
from plasTeX.TeX import TeX


from nti.contentrendering.tests import simpleLatexDocumentText, ConfiguringTestBase, buildDomFromString


from nti.contentrendering.resources import interfaces
from nti.contentrendering.resources.converters import ImagerContentUnitRepresentationBatchConverter, AbstractLatexCompilerDriver, AbstractCompilingContentUnitRepresentationBatchConverter

from nti.tests import verifiably_provides

class TestImagerContentUnitRepresentationBatchConverter(ConfiguringTestBase):


	def test_generator(self):
		class Image(object):
			path = 'path'
		class Imager(object):
			fileExtension = '.png'
			def __init__( self, document ):
				pass
			def newImage( self, source ):
				return Image()
			def close(self): pass


		converter = ImagerContentUnitRepresentationBatchConverter( buildDomFromString( simpleLatexDocumentText( '' ) ), Imager )
		assert_that( converter, verifiably_provides( interfaces.IContentUnitRepresentationBatchConverter ) )

		class ContentUnit(object):
			source = "abc"

		assert_that( converter.process_batch( [ContentUnit] ), contains( verifiably_provides( interfaces.IFilesystemContentUnitRepresentation ) ) )
		assert_that( converter.process_batch( [] ), is_( () ) )


class TestAbstractLatexCompiler(ConfiguringTestBase):

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
