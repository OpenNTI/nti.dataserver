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

import unittest
from hamcrest import is_
from hamcrest import is_not
from hamcrest import assert_that
from hamcrest import has_entry
from hamcrest import has_entries
from hamcrest import has_length
from hamcrest import has_key
from hamcrest import contains_string
does_not = is_not
from hamcrest import has_property
from hamcrest import greater_than
from hamcrest import has_item


from nti.testing.matchers import validly_provides as verifiably_provides
from nose.tools import assert_raises
import itertools


from nti.appserver import interfaces as app_interfaces
from nti.appserver.account_creation_views import account_create_view, account_preflight_view


from nti.app.testing.testing import ITestMailDelivery
from nti.app.testing.layers import NewRequestSharedConfiguringTestLayer
from nti.app.testing.base import TestBaseMixin

import pyramid.httpexceptions as hexc

from nti.dataserver.interfaces import IShardLayout, INewUserPlacer
from nti.dataserver import users

from nti.dataserver import shards
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans
from nti.externalization.externalization import to_json_representation

from nti.dataserver.users import interfaces as user_interfaces

from zope.component import eventtesting
from zope import component
from zope.lifecycleevent import IObjectCreatedEvent, IObjectAddedEvent
from zope.annotation.interfaces import IAnnotations

import datetime


class _AbstractValidationViewBase(TestBaseMixin):
	""" Base for the things where validation should fail """

	the_view = None

	@WithMockDSTrans
	def test_create_invalid_realname(self):
		self.request.content_type = b'application/vnd.nextthought+json'
		self.request.body = to_json_representation( {'Username': 'jason@test.nextthought.com',
													 'password': 'pass123word',
													 'realname': '123 456_',
													 'email': 'foo@bar.com',} )

		with assert_raises( hexc.HTTPUnprocessableEntity ) as exc:
			self.the_view( self.request )


		assert_that( exc.exception.json_body, has_entry( 'field', 'realname' ) )
		assert_that( exc.exception.json_body, has_entry( 'code', 'RealnameInvalid' ) )
		assert_that( exc.exception.json_body, has_entry( 'value', '123 456_' ) )
		assert_that( exc.exception.json_body, has_entry( 'message', contains_string( 'The first or last name you have entered is not valid.' ) ) )

	@WithMockDSTrans
	def test_create_invalid_invitation_code(self):
		self.request.content_type = b'application/vnd.nextthought+json'
		self.request.body = to_json_representation( {'Username': 'jason@test.nextthought.com',
													 'password': 'pass123word',
													 'realname': 'Jason Madden',
													 'email': 'foo@bar.com',
													 'invitation_codes': ['foobar'] } )

		with assert_raises( hexc.HTTPUnprocessableEntity ) as exc:
			self.the_view( self.request )


		assert_that( exc.exception.json_body, has_entry( 'field', 'invitation_codes' ) )
		assert_that( exc.exception.json_body, has_entry( 'code', 'InvitationCodeError' ) )
		assert_that( exc.exception.json_body, has_entry( 'value', 'foobar' ) )
		assert_that( exc.exception.json_body, has_entry( 'message', contains_string( 'The invitation code is not valid.' ) ) )

	@WithMockDSTrans
	def test_create_valid_invitation_code(self):
		users.Community.create_entity( username='MATHCOUNTS' )
		self.request.content_type = b'application/vnd.nextthought+json'
		self.request.body = to_json_representation( {'Username': 'jason@test.nextthought.com',
													 'password': 'pass123word',
													 'realname': 'Jason Madden',
													 'email': 'foo@bar.com',
													 'invitation_codes': ['MATHCOUNTS'] } )

		self.the_view( self.request )


	@WithMockDSTrans
	def test_create_short_invalid_password(self):
		self.request.content_type = b'application/vnd.nextthought+json'
		self.request.body = to_json_representation( {'Username': 'foo@bar.com',
													 'email': 'foo@bar.com',
													 'password': 'a' } )
		with assert_raises( hexc.HTTPUnprocessableEntity ) as exc:
			self.the_view( self.request )


		assert_that( exc.exception.json_body, has_entry( 'field', 'password' ) )
		assert_that( exc.exception.json_body, has_entry( 'message', contains_string( 'Your password is too short. Please choose one at least' ) ) )
		assert_that( exc.exception.json_body, has_entry( 'code', 'TooShortPassword' ) )

	@WithMockDSTrans
	def test_create_insecure_invalid_password(self):
		self.request.content_type = b'application/vnd.nextthought+json'
		self.request.body = to_json_representation( {'Username': 'foo@bar.com',
													 'email': 'foo@bar.com',
													 'password': 'donald' } )
		with assert_raises( hexc.HTTPUnprocessableEntity ) as exc:
			self.the_view( self.request )


		assert_that( exc.exception.json_body, has_entry( 'field', 'password' ) )
		assert_that( exc.exception.json_body, has_entry( 'code', 'InsecurePasswordIsForbidden' ) )



	@WithMockDSTrans
	def test_create_invalid_email( self ):
		self.request.content_type = b'application/vnd.nextthought+json'
		self.request.body = to_json_representation( {'Username': 'jason@test.nextthought.com',
													 'password': 'pass132word',
													 'email': 'not valid' } )

		with assert_raises( hexc.HTTPUnprocessableEntity ) as e:
			self.the_view( self.request )

		assert_that( e.exception.json_body, has_entry( 'code', 'EmailAddressInvalid' ) )
		assert_that( e.exception.json_body, has_entry( 'field', 'email' ) )

	@WithMockDSTrans
	def test_create_censored_username( self ):
		self.request.content_type = b'application/vnd.nextthought+json'
		self.request.body = to_json_representation( {'Username': 'FatBastard',
													 'password': 'pass132word',
													 'email': 'foo@bar.com' } )

		with assert_raises( hexc.HTTPUnprocessableEntity ) as e:
			self.the_view( self.request )

		assert_that( e.exception.json_body, has_entry( 'code', 'FieldContainsCensoredSequence' ) )
		assert_that( e.exception.json_body, has_entry( 'field', 'Username' ) )


	@WithMockDSTrans
	def test_create_invalid_username( self ):
		self.request.content_type = 'application/vnd.nextthought+json'

		bad_code = 'UsernameCannotBeBlank'
		bad_code = [bad_code] + ['UsernameContainsIllegalChar'] * 4
		bad_code.append( "TooShort" )
		for bad_code, bad_username in itertools.izip( bad_code, ('   ', 'foo bar', 'foo#bar', 'foo,bar', 'foo%bar', 'abcd' )):

			self.request.body = to_json_representation( {'Username': bad_username,
														 'password': 'pass132word',
														 'realname': 'Joe Human',
														 'email': 'user@domain.com' } )
			__traceback_info__ = self.request.body


			with assert_raises( hexc.HTTPUnprocessableEntity ) as e:
				self.the_view( self.request )

			assert_that( e.exception.json_body, has_entry( 'field', 'Username' ) )
			assert_that( e.exception.json_body, has_entry( 'code', bad_code ) )

		# last one is too short.
		assert_that( e.exception.json_body, has_entry( 'message', contains_string('Username is too short. Please use at least' ) ) )

from nti.app.testing.layers import NonDevmodeNewRequestSharedConfiguringTestLayer

class _AbstractNotDevmodeViewBase(TestBaseMixin):
	# The tests that depend on not having devmode installed (stricter default validation) should be here
	# Since they run so much slower due to the mimetype registration

	the_view = None

	@WithMockDSTrans
	def test_create_censored_username( self ):
		self.request.content_type = 'application/vnd.nextthought+json'
		self.request.body = to_json_representation( {'Username': 'shpxsnpr'.encode('rot13'),
													 'password': 'pass132word',
													 'email': 'foo@bar.com' } )


		with assert_raises( hexc.HTTPUnprocessableEntity ) as e:
			self.the_view( self.request )

		assert_that( e.exception.json_body, has_entry( 'code', 'FieldContainsCensoredSequence' ) )
		assert_that( e.exception.json_body, has_entry( 'field', 'Username' ) )
		assert_that( e.exception.json_body, has_entry( 'message', contains_string( 'censored' ) ) )


	@WithMockDSTrans
	def test_create_censored_alias( self ):
		self.request.content_type = 'application/vnd.nextthought+json'
		self.request.body = to_json_representation( {'alias': 'shpxsnpr'.encode('rot13'),
													 'Username': 'jamadden',
													 'password': 'pass132word',
													 'email': 'foo@bar.com' } )


		with assert_raises( hexc.HTTPUnprocessableEntity ) as e:
			self.the_view( self.request )

		assert_that( e.exception.json_body, has_entry( 'code', 'FieldContainsCensoredSequence' ) )
		assert_that( e.exception.json_body, has_entry( 'field', 'alias' ) )
		assert_that( e.exception.json_body, has_entry( 'message', contains_string( 'censored' ) ) )

	@WithMockDSTrans
	def test_create_birthdate_must_be_in_past( self ):
		self.request.content_type = 'application/vnd.nextthought+json'
		self.request.body = to_json_representation( {
													 'Username': 'jamadden',
													 'realname': 'Jason Madden',
													 'password': 'pass132word',
													 'email': 'foo@bar.com',
													 'birthdate': datetime.date.today().isoformat() } )


		with assert_raises( hexc.HTTPUnprocessableEntity ) as e:
			self.the_view( self.request )

		assert_that( e.exception.json_body, has_entry( 'code', 'BirthdateInFuture' ) )
		assert_that( e.exception.json_body, has_entry( 'field', 'birthdate' ) )
		assert_that( e.exception.json_body, has_entry( 'message', contains_string( 'past' ) ) )

	@WithMockDSTrans
	def test_create_birthdate_two_digit_year( self ):
		self.request.content_type = 'application/vnd.nextthought+json'
		# This two-digit year is interpreted as in the future
		self.request.body = to_json_representation( {
													 'Username': 'jamadden',
													 'realname': 'Jason Madden',
													 'password': 'pass132word',
													 'email': 'foo@bar.com',
													 'birthdate': '63-01-01' } )

		with assert_raises( hexc.HTTPUnprocessableEntity ) as e:
			self.the_view( self.request )

		assert_that( e.exception.json_body, has_entry( 'code', 'BirthdateInFuture' ) )
		assert_that( e.exception.json_body, has_entry( 'field', 'birthdate' ) )
		assert_that( e.exception.json_body, has_entry( 'message', contains_string( 'past' ) ) )

	@WithMockDSTrans
	def test_create_birthdate_must_be_four_years_ago( self ):
		self.request.content_type = 'application/vnd.nextthought+json'
		today = datetime.date.today()
		three_years_ago = today.replace( year=today.year - 3 )
		self.request.body = to_json_representation( {
													 'Username': 'jamadden',
													 'realname': 'Jason Madden',
													 'password': 'pass132word',
													 'email': 'foo@bar.com',
													 'birthdate': three_years_ago.isoformat() } )


		with assert_raises( hexc.HTTPUnprocessableEntity ) as e:
			self.the_view( self.request )

		assert_that( e.exception.json_body, has_entry( 'code', 'BirthdateTooRecent' ) )
		assert_that( e.exception.json_body, has_entry( 'field', 'birthdate' ) )
		assert_that( e.exception.json_body, has_entry( 'message', contains_string( 'four' ) ) )


	@WithMockDSTrans
	def test_create_blank_realname( self ):

		self.request.content_type = 'application/vnd.nextthought+json'

		self.request.body = to_json_representation( {'Username': 'this_username_works',
													 'password': 'pass132word',
													 'realname': '',
													 'email': 'user@domain.com' } )
		__traceback_info__ = self.request.body


		with assert_raises( hexc.HTTPUnprocessableEntity ) as e:
			self.the_view( self.request )

		assert_that( e.exception.json_body, has_entry( 'field', 'realname' ) )
		assert_that( e.exception.json_body, has_entry( 'code', 'BlankHumanNameError' ) )
		assert_that( e.exception.json_body, has_entry( 'message', 'Please provide your first and last names.' ) )

	@WithMockDSTrans
	def test_create_invalid_realname( self ):

		self.request.content_type = 'application/vnd.nextthought+json'

		self.request.body = to_json_representation( {'Username': 'this_username_works',
													 'password': 'pass132word',
													 'realname': 'Joe',
													 'email': 'user@domain.com' } )
		__traceback_info__ = self.request.body


		with assert_raises( hexc.HTTPUnprocessableEntity ) as e:
			self.the_view( self.request )

		assert_that( e.exception.json_body, has_entry( 'field', 'realname' ) )
		assert_that( e.exception.json_body, has_entry( 'code', 'MissingLastName' ) )
		assert_that( e.exception.json_body, has_entry( 'message', 'Please provide your first and last names.' ) )

	@WithMockDSTrans
	def test_create_invalid_homepage( self ):

		self.request.content_type = 'application/vnd.nextthought+json'

		self.request.body = to_json_representation( {'Username': 'this_username_works',
													 'password': 'pass132word',
													 'realname': 'Joe Bananna',
													 'email': 'user@domain.com',
													 'home_page': 'mailto:foo@bar.com'} )
		__traceback_info__ = self.request.body


		with assert_raises( hexc.HTTPUnprocessableEntity ) as e:
			self.the_view( self.request )

		assert_that( e.exception.json_body, has_entry( 'field', 'home_page' ) )
		assert_that( e.exception.json_body, has_entry( 'code', 'InvalidURI' ) )
		assert_that( e.exception.json_body, has_entry( 'message', 'The specified URI is not valid.' ) )

class TestPreflightView(unittest.TestCase,_AbstractValidationViewBase):
	layer = NewRequestSharedConfiguringTestLayer

	def setUp( self ):
		super(TestPreflightView,self).setUp()
		self.the_view = account_preflight_view


	@WithMockDSTrans
	def test_preflight_username_only_with_email( self ):
		# see site_policies.[py|zcml]
		assert_that( self.request.host, is_( 'example.com:80' ) )
		self.request.headers[b'origin'] = b'http://rwanda.nextthought.com'

		self.request.content_type = 'application/vnd.nextthought+json'
		self.request.body = to_json_representation( {'Username': 'jason@test.nextthought.com',
													 'birthdate': '1982-01-31'} )
		new_user = self.the_view( self.request )
		# XXX: We've gone back and forth on asserting whether this should
		# be 0 or 24. 0 actually doesn't make any sense to me, but it was the original
		# value
		assert_that( new_user, has_entry( 'AvatarURLChoices', has_length( 0 ) ) )

		self.request.body = to_json_representation( {'Username': 'jason@example',
													 'birthdate': '1982-01-31'} )

		with assert_raises( hexc.HTTPUnprocessableEntity ) as e:
			self.the_view( self.request )

		assert_that( e.exception.json_body, has_entry( 'field', 'Username' ) )
		assert_that( e.exception.json_body, has_entry( 'code', 'EmailAddressInvalid' ) )
		assert_that( e.exception.json_body, has_entry( 'message', 'The email address you have entered is not valid.' ) )


class TestCreateViewNotDevmode(unittest.TestCase,_AbstractNotDevmodeViewBase):
	layer = NonDevmodeNewRequestSharedConfiguringTestLayer
	def setUp( self ):
		super(TestCreateViewNotDevmode,self).setUp()
		self.the_view = account_create_view

	@WithMockDSTrans
	def test_create_works( self ):
		# username result
		# events
		# headers
		self.request.content_type = 'application/vnd.nextthought+json'
		self.request.body = to_json_representation( {'Username': 'jason@test.nextthought.com',
													 'password': 'pass123word',
													 'realname': 'Jason Madden',
													 'email': 'foo@bar.com' } )


		new_user = account_create_view( self.request )
		assert_that( new_user, has_property( 'username', 'jason@test.nextthought.com' ) )
		assert_that( user_interfaces.IFriendlyNamed( new_user ), has_property( 'alias', 'Jason Madden' ) )
		assert_that( self.request.response, has_property( 'location', contains_string( '/dataserver2/users/jason%40test.nextthought.com' ) ) )
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
													 'realname': 'Jason Madden',
													 'email': 'foo@bar.com' } )

		new_user = account_create_view( self.request )
		assert_that( user_interfaces.IFriendlyNamed( new_user ), has_property( 'alias', 'Jason Madden' ) )

		with assert_raises( hexc.HTTPConflict ) as e:
			account_create_view( self.request )

		assert_that( e.exception.json_body, has_entry( 'code', 'DuplicateUsernameError' ) )


class TestCreateView(unittest.TestCase,_AbstractValidationViewBase):
	layer = NewRequestSharedConfiguringTestLayer
	def setUp( self ):
		super(TestCreateView,self).setUp()
		self.the_view = account_create_view

	@WithMockDSTrans
	def test_create_missing_username( self ):
		self.request.content_type = b'application/vnd.nextthought+json'
		self.request.body = to_json_representation( {'password': 'pass123word', 'email': 'foo@bar.com' } )
		with assert_raises( hexc.HTTPUnprocessableEntity ):
			self.the_view( self.request )


	@WithMockDSTrans
	def test_create_missing_password(self):
		self.request.content_type = b'application/vnd.nextthought+json'
		self.request.body = to_json_representation( {'Username': 'foo@bar.com', 'email': 'foo@bar.com' } )
		with assert_raises( hexc.HTTPUnprocessableEntity ):
			account_create_view( self.request )

	@WithMockDSTrans
	def test_create_null_password(self):
		self.request.content_type = b'application/vnd.nextthought+json'
		self.request.body = to_json_representation( {'Username': 'foo@bar.com',
													 'email': 'foo@bar.com',
													 'password': None } )
		with assert_raises( hexc.HTTPUnprocessableEntity ) as exc:
			self.the_view( self.request )


		assert_that( exc.exception.json_body, has_entry( 'field', 'password' ) )
		#assert_that( exc.exception.json_body, has_entry( 'message', contains_string( 'Password is too short' ) ) )
		#assert_that( exc.exception.json_body, has_entry( 'code', 'TooShortPassword' ) )

	@WithMockDSTrans
	def test_create_shard_matches_request_host( self ):
		assert_that( self.request.host, is_( 'example.com:80' ) )
		mock_dataserver.add_memory_shard( self.ds, 'example.com' )

		self.request.content_type = b'application/vnd.nextthought+json'
		self.request.body = to_json_representation( {'Username': 'jason@test.nextthought.com',
													 'password': 'pass123word',
													 'realname': 'Jason Madden',
													 'email': 'foo@bar.com' } )


		new_user = account_create_view( self.request )

		assert_that( new_user._p_jar.db(), has_property( 'database_name', 'example.com' ) )

		assert_that( new_user, has_property( '__parent__', IShardLayout( mock_dataserver.current_transaction ).users_folder ) )

	@WithMockDSTrans
	def test_create_shard_matches_request_origin( self ):
		assert_that( self.request.host, is_( 'example.com:80' ) )
		self.request.headers[b'origin'] = b'http://content.nextthought.com'
		mock_dataserver.add_memory_shard( self.ds, 'content.nextthought.com' )

		self.request.content_type = 'application/vnd.nextthought+json'
		self.request.body = to_json_representation( {'Username': 'jason@test.nextthought.com',
													 'password': 'pass123word',
													 'realname': 'Jason Madden',
													 'email': 'foo@bar.com' } )


		new_user = account_create_view( self.request )

		assert_that( new_user._p_jar.db(), has_property( 'database_name', 'content.nextthought.com' ) )

		assert_that( new_user, has_property( '__parent__', IShardLayout( mock_dataserver.current_transaction ).users_folder ) )


	@WithMockDSTrans
	def test_create_component_matches_request_host( self ):
		assert_that( self.request.host, is_( 'example.com:80' ) )
		mock_dataserver.add_memory_shard( self.ds, 'FOOBAR' )
		class Placer(shards.AbstractShardPlacer):
			def placeNewUser( self, user, users_directory, _shards ):
				self.place_user_in_shard_named( user, users_directory, 'FOOBAR' )
		utility = Placer()
		component.provideUtility( utility, provides=INewUserPlacer, name='example.com' )
		try:
			self.request.content_type = b'application/vnd.nextthought+json'
			self.request.body = to_json_representation( {'Username': 'jason@test.nextthought.com',
														 'password': 'pass123word',
														 'realname': 'Jason Madden',
														 'email': 'foo@bar.com' } )


			new_user = account_create_view( self.request )

			assert_that( new_user._p_jar.db(), has_property( 'database_name', 'FOOBAR' ) )

			assert_that( new_user, has_property( '__parent__', IShardLayout( mock_dataserver.current_transaction ).users_folder ) )
		finally:
			component.getGlobalSiteManager().unregisterUtility( utility, provided=INewUserPlacer, name='example.com' )

from nti.app.testing.webtest import TestApp
from nti.app.testing.application_webtest import AppTestBaseMixin
from nti.app.testing.application_webtest import ApplicationLayerTest
from nti.app.testing.application_webtest import NonDevmodeApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.dataserver.tests import mock_dataserver

class _AbstractApplicationCreateUserTest(AppTestBaseMixin):

	@WithSharedApplicationMockDS
	def test_create_user( self):
		self._do_test_create_user()

	def _do_test_create_user( self, extra_environ=None ):
		app = TestApp( self.app )

		data = to_json_representation( {'Username': 'jason@test.nextthought.com',
										'password': 'pass123word',
										'realname': 'Jason Madden',
										'email': 'foo@bar.com'	} )

		path = b'/dataserver2/account.create'

		res = app.post( path, data, extra_environ=extra_environ )

		assert_that( res, has_property( 'status_int', 201 ) )
		assert_that( res, has_property( 'location', contains_string( '/dataserver2/users/jason' ) ) )

		assert_that( res.headers, has_key( 'Set-Cookie' ) )
		assert_that( res.json_body, has_entry( 'Username', 'jason@test.nextthought.com' ) )
		return res

from .test_application import NonDevmodeButAnySiteApplicationTestLayer

class TestApplicationCreateUserNonDevmode(_AbstractApplicationCreateUserTest, NonDevmodeApplicationLayerTest):
	layer = NonDevmodeButAnySiteApplicationTestLayer
	@WithSharedApplicationMockDS
	def test_create_user( self ):
		super(TestApplicationCreateUserNonDevmode,self).test_create_user()
		mailer = component.getUtility( ITestMailDelivery )
		assert_that( mailer.queue, has_item( has_property( 'subject', 'Welcome to NextThought' ) ) )
		return mailer

class TestApplicationCreateUser(_AbstractApplicationCreateUserTest, ApplicationLayerTest):

	@WithSharedApplicationMockDS
	def test_create_user( self ):
		super(TestApplicationCreateUser,self).test_create_user()
		mailer = component.getUtility( ITestMailDelivery )
		assert_that( mailer.queue, has_length( 0 ) ) # no email in devmode because there is no site policy


	@WithSharedApplicationMockDS
	def test_create_user_email_site_policy(self):
		from nti.appserver.policies.site_policies import GenericSitePolicyEventListener
		from nti.appserver.policies.interfaces import ISitePolicyUserEventListener
		from zope import interface
		policy = GenericSitePolicyEventListener()
		policy.DEFAULT_EMAIL_SENDER = 'test@nextthought.com'

		from z3c.baseregistry.baseregistry import BaseComponents
		from nti.appserver.policies.sites import BASEADULT
		site = BaseComponents(BASEADULT, name='sitepolicyemailtest.nextthought.com', bases=(BASEADULT,))
		component.provideUtility(site, interface.interfaces.IComponents, name='sitepolicyemailtest.nextthought.com')

		site.registerUtility(policy)

		extra_environ = {b'HTTP_ORIGIN': b'http://sitepolicyemailtest.nextthought.com'}

		res = super(TestApplicationCreateUser,self)._do_test_create_user(extra_environ=extra_environ)
		assert_that( res.json_body, has_entry('email', 'foo@bar.com'))

		mailer = component.getUtility( ITestMailDelivery )
		assert_that( mailer.queue, has_item( has_property( 'subject', 'Welcome to NextThought' ) ) )
		assert_that( mailer.queue, has_item( has_entry('From', policy.DEFAULT_EMAIL_SENDER ) ) )



	@WithSharedApplicationMockDS
	def test_create_user_logged_in( self ):
		with mock_dataserver.mock_db_trans(self.ds):
			_ = self._create_user( )

		app = TestApp( self.app )
		data = to_json_representation( {'Username': 'jason@test.nextthought.com',
										'password': 'password' } )

		path = b'/dataserver2/account.create'

		_ = app.post( path, data, extra_environ=self._make_extra_environ(), status=403 )

class TestApplicationPreflightUser(_AbstractApplicationCreateUserTest, ApplicationLayerTest):


	@WithSharedApplicationMockDS
	def test_preflight_user( self ):
		app = TestApp( self.app )


		data_with_username_only = {'Username': 'jason@test.nextthought.com'}
		data_full = {'Username': 'jason@test.nextthought.com',
					 'password': 'pass123word',
					 'email': 'foo@bar.com'	}

		path = b'/dataserver2/account.preflight.create'

		for data in (data_with_username_only, data_full):
			data = to_json_representation( data )
			res = app.post( path, data )

			assert_that( res, has_property( 'status_int', 200 ) )

class TestApplicationProfile(_AbstractApplicationCreateUserTest, ApplicationLayerTest):

	@WithSharedApplicationMockDS
	def test_preflight_user( self ):
		with mock_dataserver.mock_db_trans(self.ds):
			self._create_user()

		app = TestApp( self.app )

		# In the generic policy
		path = b'/dataserver2/users/sjohnson@nextthought.com/@@account.profile'
		res = app.get( path, extra_environ=self._make_extra_environ() )

		assert_that( res, has_property( 'status_int', 200 ) )
		assert_that( res.json_body, has_entry( 'ProfileSchema', has_key( 'opt_in_email_communication' ) ) )
		assert_that( res.json_body['ProfileSchema'], does_not( has_key( 'birthCountry' ) ) )

		# Same user in the columbia policy has more fields
		environ = self._make_extra_environ()
		environ[b'HTTP_ORIGIN'] = b'http://columbia.nextthought.com'
		res = app.get( path, extra_environ=environ )

		assert_that( res, has_property( 'status_int', 200 ) )
		assert_that( res.json_body, has_entry( 'ProfileSchema', has_key( 'opt_in_email_communication' ) ) )
		assert_that( res.json_body['ProfileSchema'], has_key( 'birthCountry' ) )


	@WithSharedApplicationMockDS(users=True,testapp=True)
	def test_migrate_columbia_profile(self):

		# In the normal environment, set our email address
		self.testapp.put_json( '/dataserver2/users/sjohnson@nextthought.com/++fields++email',
							   'jason.madden@nextthought.com' )

		me = self.resolve_user()
		assert_that( me, has_entry( 'email', 'jason.madden@nextthought.com' ) )

		# Now we can access it in the columbia page, where we also get some
		# new empty fields
		extra_environ = {b'HTTP_ORIGIN': b'http://columbia.nextthought.com'}
		self.testapp.put_json( '/dataserver2/users/sjohnson@nextthought.com/',
							   {'birthCountry': 'us'},
							   extra_environ=extra_environ)

		me = self.resolve_user(extra_environ=extra_environ)
		assert_that( me, has_entry( 'email', 'jason.madden@nextthought.com' ) )
		assert_that( me, has_entry( 'birthCountry', 'us' ) )


def main(email=None, uname=None, cname=None):
	import sys
	_contact_email = email or sys.argv[1]
	_username = uname or sys.argv[2]
	child_name = cname or sys.argv[3]

	from zope import interface
	from zope.annotation.interfaces import IAttributeAnnotatable
	@interface.implementer(user_interfaces.IUserProfile,IAttributeAnnotatable,app_interfaces.IContactEmailRecovery)
	class FakeUser(object):
		username = _username
		contact_email = _contact_email
		realname = child_name

	class FakeEvent(object):
		request = True

	import nti.dataserver.utils
	from pyramid.testing import setUp as psetUp
	from pyramid.testing import DummyRequest
	nti.dataserver.utils._configure( set_up_packages=('nti.appserver',) )
	request = DummyRequest()
	config = psetUp(registry=component.getGlobalSiteManager(),request=request,hook_zca=False)
	config.setup_registry()
	FakeEvent.request = request

	import pyramid_mailer
	from pyramid_mailer.interfaces import IMailer
	component.provideUtility( pyramid_mailer.Mailer.from_settings( {'mail.queue_path': '/tmp/ds_maildir', 'mail.default_sender': 'no-reply@nextthought.com' } ), IMailer )

	import nti.app.pyramid_zope.z3c_zpt
	from pyramid.interfaces import IRendererFactory
	component.provideUtility( nti.app.pyramid_zope.z3c_zpt.renderer_factory, IRendererFactory, name='.pt' )
	import nti.appserver.policies.user_policies
	nti.appserver.policies.user_policies.send_consent_request_on_new_coppa_account(FakeUser(), FakeEvent)

	import transaction
	transaction.commit()

if __name__ == '__main__':
	main()
