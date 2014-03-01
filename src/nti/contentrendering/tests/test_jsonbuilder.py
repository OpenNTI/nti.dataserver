#!/usr/bin/env python
# -*- coding: utf-8 -*-
# $Id$

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904


from . import ContentrenderingLayerTest
from nti.contentrendering.utils import NoConcurrentPhantomRenderedBook
from nti.contentrendering import jsonpbuilder
from nti.testing.matchers import provides
from nti.contentrendering import interfaces

import base64
import io
import mimetypes
import os
import shutil
from hamcrest import assert_that
from hamcrest import has_entry
from hamcrest import has_item
from hamcrest import has_property
from hamcrest import is_
from hamcrest import is_not
from hamcrest import none
import simplejson as json

def _loadJSONP( filename ):
	jsonpdata = None
	with io.open( filename, 'rb') as file:
		jsonpdata = file.read()

	_t = jsonpdata.rstrip(');').split('(',1)
	return ( _t[0], json.loads(_t[1]))

def _verifyJSONPContents( orig_filename, ntiid, jsonpFunctionName ):
	data = _loadJSONP( orig_filename + '.jsonp' )
	refData = None
	with io.open( orig_filename, 'rb') as file:
		refData = base64.standard_b64encode(file.read())

	assert_that( data, has_item( jsonpFunctionName ) )
	assert_that( data[1], has_entry('ntiid',  ntiid ) )
	assert_that( data[1], has_entry('Content-Type', mimetypes.guess_type( orig_filename )[0]) )
	assert_that( data[1], has_entry('Content-Encoding', 'base64') )
	assert_that( data[1], has_entry('content', refData) )
	assert_that( data[1], has_entry('version', '1' ) )

class TestTransforms(ContentrenderingLayerTest):


	def test_module_provides(self):
		assert_that( jsonpbuilder, provides(interfaces.IRenderedBookTransformer ) )


	def test_transform(self):
		#"""Verify the transform produces correct JSONP output for the ToC file, index.html, and the
		#root icon file.
		#"""

		# Make a copy of the rendered book
		book_copy = os.path.join( os.path.dirname( __file__ ),  'test-tmp' )
		if os.path.exists( book_copy ):
			shutil.rmtree(book_copy, ignore_errors=True)
		shutil.copytree( os.path.join( os.path.dirname( __file__ ),  'NextThoughtGenericTutorial-rendered-book'), book_copy)

		try:
			# Open the copy of the rendered book

			book = NoConcurrentPhantomRenderedBook( None, book_copy )

			# Assert ToC is present
			assert_that( book, has_property( 'toc', is_not( none() ) ) )
			# Assert that the root topic is present
			assert_that( book.toc, has_property( 'root_topic', is_not( none() ) ) )
			# Assert that there is a root topic icon is present
			assert_that( book.toc.root_topic.get_icon(), is_not( none() ) )
			# Assert that there is a root topic icon file exists
			assert_that( os.path.exists(os.path.join(book_copy, book.toc.root_topic.get_icon())), is_( True ) )

			jsonpbuilder.transform( book )

			# Assert that eclipse-toc.xml.jsonp exists
			assert_that( os.path.exists( book.toc.filename + '.jsonp'), is_( True ) )
			# Assert that index.html.jsonp exists
			assert_that( os.path.exists(os.path.join(book_copy, book.toc.root_topic.filename) + '.jsonp'),is_( True ) )
			# Assert that the JSONP version of the root topic icon file exists
			assert_that( os.path.exists(os.path.join(book_copy, book.toc.root_topic.get_icon()) + '.jsonp'),is_( True ) )

			# Test that the eclipse-toc.xml.jsonp contains the correct data
			_verifyJSONPContents( book.toc.filename, book.toc.root_topic.ntiid, 'jsonpToc' )
			# Test that the index.html.jsonp contains the correct data
			_verifyJSONPContents( os.path.join(book_copy, book.toc.root_topic.filename),
					      book.toc.root_topic.ntiid, 'jsonpContent' )
			# Test that the JSONP version of the root topic icon file  contains the correct data
			_verifyJSONPContents( os.path.join(book_copy, book.toc.root_topic.get_icon()),
					      book.toc.root_topic.ntiid, 'jsonpData' )

		finally:
			# Delete copy of the rendered book
			shutil.rmtree( book_copy )
