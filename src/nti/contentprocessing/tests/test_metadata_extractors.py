#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904


from hamcrest import assert_that
from hamcrest import is_
from hamcrest import has_key
from hamcrest import has_entry
from hamcrest import contains
from hamcrest import contains_inanyorder
from hamcrest import has_property, has_properties

import nti.tests
from nti.tests import validly_provides
import fudge

from nti.contentprocessing import metadata_extractors, interfaces

import os.path
from rdflib import Graph



setUpModule = lambda: nti.tests.module_setup( set_up_packages=('nti.contentprocessing',) )
tearDownModule = nti.tests.module_teardown

def test_metadata_provides():

	metadata = metadata_extractors.ContentMetadata()
	assert_that( metadata, validly_provides( interfaces.IContentMetadata ) )

def test_opengraph_extraction_from_file():
	# Originally from NewYorker
	#  http://www.newyorker.com/reporting/2013/01/07/130107fa_fact_green?currentPage=all
	the_file = os.path.abspath( os.path.join( os.path.dirname(__file__),
											  'og_metadata.html') )

	graph = Graph()
	graph.parse( the_file, format='rdfa' )

	args = metadata_extractors._file_args( the_file )


	def _check(result):
		assert_that( result, has_property( 'title', 'Adam Green: The Spectacular Thefts of Apollo Robbins, Pickpocket' ) )
		assert_that( result, has_property( 'href', 'http://www.newyorker.com/reporting/2013/01/07/130107fa_fact_green' ) )
		assert_that( result, has_property( 'images', contains( has_property( 'url', 'http://www.newyorker.com/images/2013/01/07/g120/130107_r23011_g120_cropth.jpg') ) ) )
		assert_that( result, validly_provides( interfaces.IContentMetadata ) )

	result = metadata_extractors._HTMLExtractor()._extract_opengraph(metadata_extractors.ContentMetadata(), args )
	_check( result )

	result = metadata_extractors.get_metadata_from_content_location( the_file )
	_check( result )

def test_twitter_extraction_from_file():
	# Originally from NYTimes:
	# https://www.nytimes.com/2013/05/17/health/exercise-class-obedience-not-required.html
	the_file = os.path.abspath( os.path.join( os.path.dirname(__file__),
											  'twitter_metadata.html') )

	graph = Graph()
	graph.parse( the_file, format='rdfa' )

	args = metadata_extractors._file_args( the_file )

	def _check(result):
		assert_that( result, has_property( 'title', 'Exercise Class, Obedience Not Required' ) )
		assert_that( result, has_property( 'href', 'http://www.nytimes.com/2013/05/17/health/exercise-class-obedience-not-required.html' ) )
		assert_that( result, has_property( 'images', contains( has_property( 'url', 'http://graphics8.nytimes.com/images/2013/05/17/arts/17URBAN_SPAN/17URBAN_SPAN-thumbLarge-v2.jpg' ) ) ) )
		assert_that( result, validly_provides( interfaces.IContentMetadata ) )

	result = metadata_extractors._HTMLExtractor()._extract_twitter(metadata_extractors.ContentMetadata(), args )
	_check( result )


def test_opengraph_extraction():
	template = """
	<html %s>
	<head>
	<title>The Rock (1996)</title>
	<meta property="og:title" content="The Rock" />
	<meta property="og:type" content="video.movie" />
	<meta property="og:url" content="http://www.imdb.com/title/tt0117500/" />
	<meta property="og:image" content="http://ia.media-imdb.com/images/rock.jpg" />

	<meta property="og:image:width" content="300" />
	<meta property="og:image:height" content="400" />

	</head>

	</html>"""


	class _args(object):
		__name__ = None
		text = None

	# No explicit prefix (relying on default in RDFa 1.1), an HTML5-style prefix,
	# and the XML style prefix
	for prefix in '', 'prefix="og: http://ogp.me/ns#"', 'xmlns:og="http://opengraphprotocol.org/schema/"':
		html = template % prefix
		__traceback_info__ = html
		args = _args()
		args.__name__ = 'http://example.com'
		args.text = html

		result = metadata_extractors._HTMLExtractor()._extract_opengraph(metadata_extractors.ContentMetadata(), args )

		assert_that( result, has_property( 'title', 'The Rock' ) )
		assert_that( result, has_property( 'href', 'http://www.imdb.com/title/tt0117500/' ) )
		# For one image, we can preserve the width and height, if given
		assert_that( result, has_property( 'images', contains( has_properties(
			'url', 'http://ia.media-imdb.com/images/rock.jpg',
			'width', 300,
			'height', 400 ) ) ) )
		assert_that( result, validly_provides( interfaces.IContentMetadata ) )

def test_opengraph_extraction_multiple_images():
	template = """
	<html %s>
	<head>
	<title>The Rock (1996)</title>
	<meta property="og:title" content="The Rock" />
	<meta property="og:type" content="video.movie" />
	<meta property="og:url" content="http://www.imdb.com/title/tt0117500/" />

	<meta property="og:image" content="http://example.com/rock.jpg" />
	<meta property="og:image:width" content="300" />
	<meta property="og:image:height" content="300" />
	<meta property="og:image" content="http://example.com/rock2.jpg" />
	<meta property="og:image" content="http://example.com/rock3.jpg" />
	<meta property="og:image:height" content="1000" />
	<meta property="og:image:width" content="1000" />
	"""

	class _args(object):
		__name__ = None
		text = None

	for prefix in '', 'prefix="og: http://ogp.me/ns#"', 'xmlns:og="http://opengraphprotocol.org/schema/"':
		html = template % prefix
		__traceback_info__ = html
		args = _args()
		args.__name__ = 'http://example.com'
		args.text = html

		result = metadata_extractors._HTMLExtractor()._extract_opengraph(metadata_extractors.ContentMetadata(), args )

		assert_that( result, has_property( 'title', 'The Rock' ) )
		assert_that( result, has_property( 'href', 'http://www.imdb.com/title/tt0117500/' ) )
		# Sadly, order is not preserved
		assert_that( result, has_property( 'images', contains_inanyorder( has_property( 'url', 'http://example.com/rock.jpg' ),
																		  has_property( 'url', 'http://example.com/rock2.jpg' ),
																		  has_property( 'url', 'http://example.com/rock3.jpg' ) ) ) )



@fudge.patch('requests.get')
def test_extraction_remote_pdf(fake_get=None):
	# By commenting out the patch line, we can test with a real file
	if fake_get is not None:
		# This real URL has been download locally
		pdf_file = os.path.join( os.path.dirname( __file__ ), 'test_page574_12.pdf' )

		class R1(object):
			def __init__(self):
				self.headers = {'content-type': 'application/pdf'}
				self.raw = open(pdf_file, 'rb')

		fake_get.is_callable().returns( R1() )
		href = 'http://someserver.com/path/to/test_page574_12.pdf' # remote href
	else:
		href = 'http://support.pokemon.com/FileManagement/Download/f6029520f8ea43f08790ec4975944bb3'

	result = metadata_extractors.get_metadata_from_content_location( href )

	# Values from the PDF
	assert_that( result, has_property( 'creator', 'Jason Madden' ) )
	assert_that( result, has_property( 'description', 'Subject' ) )
