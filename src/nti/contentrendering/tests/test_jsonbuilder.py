from . import ConfiguringTestBase
from nti.contentrendering import RenderedBook
from nti.contentrendering import jsonpbuilder
from nti.tests import provides
from nti.contentrendering import interfaces

import base64
import io
import mimetypes
import os
import shutil
from hamcrest import assert_that, has_length, greater_than_or_equal_to, is_, none
import simplejson as json

def test_module_provides():
	assert_that( jsonpbuilder, provides(interfaces.IRenderedBookTransformer ) )

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
		
	assert_that( data[0], is_( jsonpFunctionName ) )
	assert_that( data[1]['ntiid'], is_( ntiid ) )
	assert_that( data[1]['Content-Type'], is_( mimetypes.guess_type( orig_filename )[0] ) )
	assert_that( data[1]['Content-Encoding'], is_( 'base64' ) )
	assert_that( data[1]['content'], is_( refData ) )
	assert_that( data[1]['version'], is_( '1' ) )

class TestTransforms(ConfiguringTestBase):

	def test_transform(self):
		"""Verify the transform produces correct JSONP output for the ToC file, index.html, and the
		root icon file.
		"""

		# Make a copy of the rendered book
		book_copy = os.path.join( os.path.dirname( __file__ ),  'test-tmp' )
		shutil.rmtree(book_copy, ignore_errors=True)
		shutil.copytree( os.path.join( os.path.dirname( __file__ ),  'NextThoughtGenericTutorial-rendered-book'), book_copy)
		
		# Open the copy of the rendered book
		book = RenderedBook.RenderedBook( None, book_copy )

		# Assert ToC is present
		assert_that( (book.toc is not None) , is_( True ) )
		# Assert that the root topic is present
		assert_that( (book.toc.root_topic is not None) , is_( True ) )
		# Assert that there is a root topic icon is present
		assert_that( (book.toc.root_topic.get_icon() is not None) , is_( True ) )
		# Assert that there is a root topic icon file exists
		assert_that( os.access(os.path.join(book_copy, book.toc.root_topic.get_icon()), os.F_OK),
			     is_( True ) )

		jsonpbuilder.transform( book )

		# Assert that eclipse-toc.xml.jsonp exists
		assert_that( os.access( book.toc.filename + '.jsonp', os.F_OK), is_( True ) )
		# Assert that index.html.jsonp exists
		assert_that( os.access(os.path.join(book_copy, book.toc.root_topic.filename) + '.jsonp', os.F_OK),
			     is_( True ) )
		# Assert that the JSONP version of the root topic icon file exists
		assert_that( os.access(os.path.join(book_copy, book.toc.root_topic.get_icon()) + '.jsonp', os.F_OK),
			     is_( True ) )

		# Test that the eclipse-toc.xml.jsonp contains the correct data
		_verifyJSONPContents( book.toc.filename, book.toc.root_topic.ntiid, 'jsonpToc' )
		# Test that the index.html.jsonp contains the correct data
		_verifyJSONPContents( os.path.join(book_copy, book.toc.root_topic.filename), 
				      book.toc.root_topic.ntiid, 'jsonpContent' )
		# Test that the JSONP version of the root topic icon file  contains the correct data
		_verifyJSONPContents( os.path.join(book_copy, book.toc.root_topic.get_icon()), 
				      book.toc.root_topic.ntiid, 'jsonpData' )

		# Delete copy of the rendered book
		shutil.rmtree( book_copy )
