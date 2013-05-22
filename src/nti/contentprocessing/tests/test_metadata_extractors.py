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
from hamcrest import has_property

import nti.tests
from nti.tests import validly_provides

from nti.contentprocessing import metadata_extractors, interfaces

import os.path
from rdflib import Graph
from io import BytesIO


setUpModule = lambda: nti.tests.module_setup( set_up_packages=('nti.contentprocessing',) )
tearDownModule = nti.tests.module_teardown

def test_metadata_provides():

	metadata = metadata_extractors.ContentMetadata()
	assert_that( metadata, validly_provides( interfaces.IContentMetadata ) )

def test_rdflib_can_parse_file():
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
		assert_that( result, has_property( 'image', 'http://www.newyorker.com/images/2013/01/07/g120/130107_r23011_g120_cropth.jpg') )

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
		assert_that( result, has_property( 'image', 'http://graphics8.nytimes.com/images/2013/05/17/arts/17URBAN_SPAN/17URBAN_SPAN-thumbLarge-v2.jpg' ) )

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
		assert_that( result, has_property( 'image', 'http://ia.media-imdb.com/images/rock.jpg' ) )
