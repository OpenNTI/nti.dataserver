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
from hamcrest import has_entries
from hamcrest import has_length
from hamcrest import has_key
from hamcrest import contains_string
#from hamcrest import is_not
from hamcrest import has_property
from hamcrest import greater_than
from hamcrest import has_item

from nti.tests import verifiably_provides
from nose.tools import assert_raises

from nti.appserver import interfaces as app_interfaces
from nti.appserver.account_creation_views import account_create_view

from nti.appserver.tests import ConfiguringTestBase

import pyramid.httpexceptions as hexc

from nti.dataserver.interfaces import IShardLayout, INewUserPlacer
from nti.dataserver import interfaces as nti_interfaces
import nti.dataserver.tests.mock_dataserver
from nti.dataserver import shards
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans
from nti.externalization.externalization import to_json_representation
from nti.externalization.externalization import to_external_object
from nti.dataserver.users import interfaces as user_interfaces

from zope.component import eventtesting
from zope import component
from zope.lifecycleevent import IObjectCreatedEvent, IObjectAddedEvent
import zope.schema
import datetime

class TestCreateView(ConfiguringTestBase):

	features = () # Disable devmode so that we get 'email' required by default for new users

	@WithMockDSTrans
	def test_create_missing_password(self):
		self.request.content_type = 'application/vnd.nextthought+json'
		self.request.body = to_json_representation( {'Username': 'foo@bar.com', 'email': 'foo@bar.com' } )
		with assert_raises( hexc.HTTPUnprocessableEntity ):
			account_create_view( self.request )

	@WithMockDSTrans
	def test_create_invalid_password(self):
		self.request.content_type = 'application/vnd.nextthought+json'
		self.request.body = to_json_representation( {'Username': 'foo@bar.com',
													 'email': 'foo@bar.com',
													 'password': 'a' } )
		with assert_raises( hexc.HTTPUnprocessableEntity ) as exc:
			account_create_view( self.request )


		assert_that( exc.exception.json_body, has_entry( 'field', 'password' ) )
		assert_that( exc.exception.json_body, has_entry( 'message', contains_string( 'Password is too short' ) ) )
		assert_that( exc.exception.json_body, has_entry( 'code', 'TooShortPassword' ) )

	@WithMockDSTrans
	def test_create_missing_username( self ):
		self.request.content_type = 'application/vnd.nextthought+json'
		self.request.body = to_json_representation( {'password': 'pass123word', 'email': 'foo@bar.com' } )
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
													 'password': 'pass123word',
													 'email': 'foo@bar.com' } )


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
		self.request.body = to_json_representation( {'Username': 'jason_nextthought_com',
													 'password': 'pass132word',
													 'email': 'foo@bar.com' } )

		account_create_view( self.request )

		with assert_raises( hexc.HTTPConflict ) as e:
			account_create_view( self.request )

		assert_that( e.exception.json_body, has_entry( 'code', 'DuplicateUsernameError' ) )

	@WithMockDSTrans
	def test_create_invalid_email( self ):
		self.request.content_type = 'application/vnd.nextthought+json'
		self.request.body = to_json_representation( {'Username': 'jason@nextthought.com',
													 'password': 'pass132word',
													 'email': 'not valid' } )



		with assert_raises( hexc.HTTPUnprocessableEntity ) as e:
			account_create_view( self.request )

		assert_that( e.exception.json_body, has_entry( 'code', 'EmailAddressInvalid' ) )
		assert_that( e.exception.json_body, has_entry( 'field', 'email' ) )

	@WithMockDSTrans
	def test_create_invalid_username( self ):
		self.request.content_type = 'application/vnd.nextthought+json'

		for bad_username in ('   ', 'foo bar', 'foo#bar', 'foo,bar', 'foo%bar' ):

			self.request.body = to_json_representation( {'Username': bad_username,
														 'password': 'pass132word',
														 'email': 'user@domain.com' } )



			with assert_raises( hexc.HTTPUnprocessableEntity ) as e:
				account_create_view( self.request )

			assert_that( e.exception.json_body, has_entry( 'field', 'Username' ) )
			assert_that( e.exception.json_body, has_entry( 'code', 'InvalidValue' ) )



	@WithMockDSTrans
	def test_create_shard_matches_request_host( self ):
		assert_that( self.request.host, is_( 'example.com:80' ) )
		mock_dataserver.add_memory_shard( self.ds, 'example.com' )

		self.request.content_type = 'application/vnd.nextthought+json'
		self.request.body = to_json_representation( {'Username': 'jason@nextthought.com',
													 'password': 'pass123word',
													 'email': 'foo@bar.com' } )


		new_user = account_create_view( self.request )

		assert_that( new_user._p_jar.db(), has_property( 'database_name', 'example.com' ) )

		assert_that( new_user, has_property( '__parent__', IShardLayout( mock_dataserver.current_transaction ).users_folder ) )

	@WithMockDSTrans
	def test_create_shard_matches_request_origin( self ):
		assert_that( self.request.host, is_( 'example.com:80' ) )
		self.request.headers['origin'] = 'http://content.nextthought.com'
		mock_dataserver.add_memory_shard( self.ds, 'content.nextthought.com' )

		self.request.content_type = 'application/vnd.nextthought+json'
		self.request.body = to_json_representation( {'Username': 'jason@nextthought.com',
													 'password': 'pass123word',
													 'email': 'foo@bar.com' } )


		new_user = account_create_view( self.request )

		assert_that( new_user._p_jar.db(), has_property( 'database_name', 'content.nextthought.com' ) )

		assert_that( new_user, has_property( '__parent__', IShardLayout( mock_dataserver.current_transaction ).users_folder ) )

	@WithMockDSTrans
	def test_create_mathcounts_policy( self ):
		# see site_policies.[py|zcml]
		assert_that( self.request.host, is_( 'example.com:80' ) )
		self.request.headers['origin'] = 'http://mathcounts.nextthought.com'

		self.request.content_type = 'application/vnd.nextthought+json'
		self.request.body = to_json_representation( {'Username': 'jason_nextthought_com',
													 'password': 'pass123word',
													 'email': 'foo@bar.com' } )


		with assert_raises( hexc.HTTPUnprocessableEntity ):
			# Cannot include username
			account_create_view( self.request )

		self.request.body = to_json_representation( {'Username': 'jason_nextthought_com',
													 'password': 'pass123word',
													 'realname': 'Joe Bananna',
													 'email': 'foo@bar.com' } )
		with assert_raises( hexc.HTTPUnprocessableEntity ):
			# username and displayname must match
			account_create_view( self.request )

		self.request.body = to_json_representation( {'Username': 'jason_nextthought_com',
													 'password': 'pass123word',
													 'realname': 'Joe Bananna',
													 'birthdate': '1982-01-31',
													 'alias': 'jason_nextthought_com',
													 'affiliation': 'school',
													 'email': 'foo@bar.com' } )
		new_user = account_create_view( self.request )
		assert_that( new_user, verifiably_provides( nti_interfaces.ICoppaUserWithoutAgreement ) )
		assert_that( new_user, has_property( 'communities', has_item( 'MathCounts' ) ) )
		assert_that( user_interfaces.IFriendlyNamed( new_user ), has_property( 'realname', 'Joe Bananna' ) )
		assert_that( user_interfaces.ICompleteUserProfile( new_user ),
					 has_property( 'birthdate', datetime.date( 1982, 1, 31 ) ) )

		assert_that( to_external_object( new_user ), has_entries( 'email', None,
																  'birthdate', None,
																  'affiliation', None ) )


	@WithMockDSTrans
	def test_create_mathcounts_policy_email_required( self ):
		# see site_policies.[py|zcml]
		assert_that( self.request.host, is_( 'example.com:80' ) )
		self.request.headers['origin'] = 'http://mathcounts.nextthought.com'

		self.request.content_type = 'application/vnd.nextthought+json'

		self.request.body = to_json_representation( {'Username': 'jason_nextthought_com',
													 'password': 'pass123word',
													 'realname': 'Joe Bananna',
													 'birthdate': '1982-01-31',
													 'alias': 'jason_nextthought_com' }  )
		with assert_raises( hexc.HTTPUnprocessableEntity ) as exc:
			 account_create_view( self.request )

		assert_that( exc.exception.json_body, has_entry( 'field', 'email' ) )

	@WithMockDSTrans
	def test_create_rwanda_policy( self ):
		# see site_policies.[py|zcml]
		assert_that( self.request.host, is_( 'example.com:80' ) )
		self.request.headers['origin'] = 'http://rwanda.nextthought.com'

		self.request.content_type = 'application/vnd.nextthought+json'
		self.request.body = to_json_representation( {'Username': 'jason@test.nextthought.com',
													 'password': 'pass123word',
													 'realname': 'Jason Madden',
													 'birthdate': '1982-01-31',
													 'alias': 'Jason',
													 'affiliation': 'NTI',
													 'email': 'jason@test.nextthought.com' } )
		new_user = account_create_view( self.request )
		assert_that( new_user, has_property( 'communities', has_item( 'CarnegieMellonUniversity' ) ) )
		assert_that( user_interfaces.IFriendlyNamed( new_user ), has_property( 'realname', 'Jason Madden' ) )
		assert_that( user_interfaces.ICompleteUserProfile( new_user ),
					 has_property( 'birthdate', datetime.date( 1982, 1, 31 ) ) )

		assert_that( to_external_object( new_user ), has_entries( 'email', 'jason@test.nextthought.com',
																  'birthdate', '1982-01-31',
																  'affiliation', 'NTI' ) )

	@WithMockDSTrans
	def test_create_component_matches_request_host( self ):
		assert_that( self.request.host, is_( 'example.com:80' ) )
		mock_dataserver.add_memory_shard( self.ds, 'FOOBAR' )
		class Placer(shards.AbstractShardPlacer):
			def placeNewUser( self, user, users_directory, _shards ):
				self.place_user_in_shard_named( user, users_directory, 'FOOBAR' )
		component.provideUtility( Placer(), provides=INewUserPlacer, name='example.com' )

		self.request.content_type = 'application/vnd.nextthought+json'
		self.request.body = to_json_representation( {'Username': 'jason@nextthought.com',
													 'password': 'pass123word',
													 'email': 'foo@bar.com' } )


		new_user = account_create_view( self.request )

		assert_that( new_user._p_jar.db(), has_property( 'database_name', 'FOOBAR' ) )

		assert_that( new_user, has_property( '__parent__', IShardLayout( mock_dataserver.current_transaction ).users_folder ) )


from .test_application import ApplicationTestBase
from webtest import TestApp
from nti.dataserver.tests import mock_dataserver

class TestApplicationCreateUser(ApplicationTestBase):

	def test_create_user( self ):
		app = TestApp( self.app )

		data = to_json_representation( {'Username': 'jason@nextthought.com',
										'password': 'password',
										'email': 'foo@bar.com'	} )

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
