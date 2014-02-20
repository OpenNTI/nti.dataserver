#!/usr/bin/env python2.7


from hamcrest import (assert_that, is_)
from nti.app.testing.layers import NewRequestLayerTest

from pyramid.request import Request

from nti.appserver.pyramid_renderers import find_content_type
from nti.externalization.externalization import toExternalObject
from ZODB.broken import Broken

class TestContentType(NewRequestLayerTest):

	def beginRequest( self, request_factory=Request.blank, request_args=('/') ):
		return super(TestContentType,self).beginRequest(request_factory, request_args)

	def test_no_accept_no_param(self):

		assert_that( find_content_type( self.request ),
					 is_( 'application/vnd.nextthought+json' ) )

	def test_generic_accept_not_overriden_by_query(self):
		self.request = Request.blank( '/?format=plist' )
		self.request.accept = '*/*'
		assert_that( find_content_type( self.request ),
					 is_( 'application/vnd.nextthought+json' ) )

	def test_xml_types_are_json( self ):
		self.request.accept = 'application/xml'

		assert_that( find_content_type( self.request, data={} ),
					 is_( 'application/vnd.nextthought+json' ) )

		self.request.accept = 'application/vnd.nextthought+json'

		assert_that( find_content_type( self.request, data={} ),
					 is_( 'application/vnd.nextthought+json' ) )


	def test_nti_type( self ):
		self.request.accept = 'application/json'

		assert_that( find_content_type( self.request, data=self ),
					 is_( 'application/vnd.nextthought.testcontenttype+json' ) )

		self.request.accept = None

		assert_that( find_content_type( self.request, data=self ),
					 is_( 'application/vnd.nextthought.testcontenttype+json' ) )

class TestRender(NewRequestLayerTest):


	def test_broken(self):
		assert_that( toExternalObject( Broken() ),
					 is_( {"Class": "BrokenObject"} ) )

		assert_that( toExternalObject( [Broken()] ),
					 is_( [{ "Class": "BrokenObject"}] ) )
