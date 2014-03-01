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
