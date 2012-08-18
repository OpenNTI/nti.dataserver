#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"


#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

logger = __import__('logging').getLogger(__name__)


from hamcrest import assert_that
from hamcrest import is_
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import has_key
from hamcrest import contains_string
#from hamcrest import is_not
from hamcrest import has_property
from hamcrest import greater_than

from nose.tools import assert_raises

from nti.appserver import interfaces as app_interfaces
from nti.appserver.account_creation_views import account_create_view

from nti.appserver.tests import ConfiguringTestBase

import pyramid.httpexceptions as hexc


from nti.dataserver.tests.mock_dataserver import WithMockDSTrans
from nti.externalization.externalization import to_json_representation


from zope.component import eventtesting
from zope import component
from zope.lifecycleevent import IObjectCreatedEvent, IObjectAddedEvent

class TestCreateView(ConfiguringTestBase):

	@WithMockDSTrans
	def test_create_missing_password(self):
		self.request.content_type = 'application/vnd.nextthought+json'
		self.request.body = to_json_representation( {'Username': 'foo@bar' } )
		with assert_raises( hexc.HTTPUnprocessableEntity ):
			account_create_view( self.request )


	@WithMockDSTrans
	def test_create_missing_username( self ):
		self.request.content_type = 'application/vnd.nextthought+json'
		self.request.body = to_json_representation( {'password': 'password' } )
		with assert_raises( hexc.HTTPUnprocessableEntity ):
			account_create_view( self.request )


	@WithMockDSTrans
	def test_create_works( self ):
		# username result
		# events
		# headers
		component.provideHandler( eventtesting.events.append, (None,) )
		self.request.content_type = 'application/vnd.nextthought+json'
		self.request.body = to_json_representation( {'Username': 'jason@nextthought.com',
														 'password': 'password' } )


		new_user = account_create_view( self.request )
		assert_that( new_user, has_property( 'username', 'jason@nextthought.com' ) )
		assert_that( self.request.response, has_property( 'location', contains_string( '/dataserver2/users/jason%40nextthought.com' ) ) )
		assert_that( self.request.response, has_property( 'status_int', 201 ) )
		#assert_that( self.request.response.headers, has_property( "what", "th" ) )

		assert_that( eventtesting.getEvents(  ), has_length( greater_than( 2 ) ) )
		assert_that( eventtesting.getEvents( app_interfaces.IUserLogonEvent ), has_length( 1 ) )
		assert_that( eventtesting.getEvents( IObjectCreatedEvent, lambda x: x.object is new_user ), has_length( 1 ) )
		assert_that( eventtesting.getEvents( IObjectAddedEvent, lambda x: x.object is new_user ), has_length( 1 ) )

	@WithMockDSTrans
	def test_create_duplicate( self ):
		self.request.content_type = 'application/vnd.nextthought+json'
		self.request.body = to_json_representation( {'Username': 'jason@nextthought.com',
													 'password': 'password' } )

		account_create_view( self.request )

		with assert_raises( hexc.HTTPConflict ):
			account_create_view( self.request )

from .test_application import ApplicationTestBase
from webtest import TestApp
from nti.dataserver.tests import mock_dataserver

class TestApplicationCreateUser(ApplicationTestBase):

	def test_create_user( self ):
		app = TestApp( self.app )

		data = to_json_representation( {'Username': 'jason@nextthought.com',
										'password': 'password' } )

		path = b'/dataserver2/users/@@account.create'

		res = app.post( path, data )

		assert_that( res, has_property( 'status_int', 201 ) )
		assert_that( res, has_property( 'location', contains_string( '/dataserver2/users/jason' ) ) )

		assert_that( res.headers, has_key( 'Set-Cookie' ) )
		assert_that( res.json_body, has_entry( 'Username', 'jason@nextthought.com' ) )

	def test_create_user_logged_in( self ):
		with mock_dataserver.mock_db_trans(self.ds):
			_ = self._create_user( )

		app = TestApp( self.app )
		data = to_json_representation( {'Username': 'jason@nextthought.com',
										'password': 'password' } )

		path = b'/dataserver2/users/@@account.create'

		res = app.post( path, data, extra_environ=self._make_extra_environ(), status=403 )
