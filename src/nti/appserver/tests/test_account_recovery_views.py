#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

logger = __import__('logging').getLogger(__name__)

from hamcrest import assert_that
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import contains_string
from hamcrest import has_property
from hamcrest import is_not as does_not
from hamcrest import has_key

from quopri import decodestring

from six.moves import urllib_parse

from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.users import interfaces as user_interfaces
from nti.dataserver import users

from zope import component
from zope import interface
from zope.lifecycleevent import modified, added


from nti.app.testing.webtest import TestApp
from nti.app.testing.application_webtest import ApplicationLayerTest
from nti.app.testing.decorators import WithSharedApplicationMockDS
from nti.dataserver.tests import mock_dataserver
from . import ITestMailDelivery

class TestApplicationUsernameRecovery(ApplicationLayerTest):

	@WithSharedApplicationMockDS
	def test_recover_user_logged_in( self ):
		with mock_dataserver.mock_db_trans(self.ds):
			_ = self._create_user( )

		app = TestApp( self.app )

		path = b'/dataserver2/logon.forgot.username'
		data = ""
		app.post( path, data, extra_environ=self._make_extra_environ(), status=403 )

	@WithSharedApplicationMockDS
	def test_recover_user_no_email( self ):
		app = TestApp( self.app )

		path = b'/dataserver2/logon.forgot.username'
		data = {}
		app.post( path, data, status=400 )

		mailer = component.getUtility( ITestMailDelivery )
		assert_that( mailer.queue, has_length( 0 ) )

	@WithSharedApplicationMockDS
	def test_recover_user_invalid_email( self ):
		app = TestApp( self.app )

		path = b'/dataserver2/logon.forgot.username'
		data = {'email': 'not valid'}
		res = app.post( path, data, status=422 )
		assert_that( res.json_body, has_entry( 'code', 'EmailAddressInvalid' ) )


		mailer = component.getUtility( ITestMailDelivery )
		assert_that( mailer.queue, has_length( 0 ) )

	@WithSharedApplicationMockDS
	def test_recover_user_not_found( self ):
		app = TestApp( self.app )

		path = b'/dataserver2/logon.forgot.username'
		data = {'email': 'not.registered@example.com'}
		app.post( path, data, status=204 )

		mailer = component.getUtility( ITestMailDelivery )
		assert_that( mailer.queue, has_length( 1 ) )

	@WithSharedApplicationMockDS
	def test_recover_user_found( self ):
		with mock_dataserver.mock_db_trans(self.ds):
			user = self._create_user( )
			user_username = user.username
			profile = user_interfaces.IUserProfile( user )
			added( profile )
			profile.email = 'jason.madden@nextthought.com'
			modified( user )

		app = TestApp( self.app )

		path = b'/dataserver2/logon.forgot.username'
		data = {'email': 'jason.madden@nextthought.com'}
		app.post( path, data, status=204 )

		mailer = component.getUtility( ITestMailDelivery )
		assert_that( mailer.queue, has_length( 1 ) )
		msg = mailer.queue[0]
		assert_that( msg, has_property( 'body' ) )
		assert_that( decodestring(msg.body), contains_string( user_username ) )

	@WithSharedApplicationMockDS
	def test_recover_multiple_user_found( self ):
		with mock_dataserver.mock_db_trans(self.ds):
			user = self._create_user( )
			user_username = user.username
			profile = user_interfaces.IUserProfile( user )
			added( profile )
			profile.email = 'jason.madden@nextthought.com'
			modified( user )

			user2 = self._create_user( username='other.user@foo.bar' )
			user2_username = user2.username
			profile = user_interfaces.IUserProfile( user2 )
			added( profile )
			profile.email = 'jason.madden@nextthought.com'
			modified( user2 )


		app = TestApp( self.app )

		path = b'/dataserver2/logon.forgot.username'
		data = {'email': 'jason.madden@nextthought.com'}
		app.post( path, data, status=204 )

		mailer = component.getUtility( ITestMailDelivery )
		assert_that( mailer.queue, has_length( 1 ) )
		msg = mailer.queue[0]

		assert_that( msg, has_property( 'body' ) )
		assert_that( decodestring(msg.body), contains_string( user_username ) )
		assert_that( decodestring(msg.body), contains_string( user2_username ) )

class TestApplicationPasswordRecovery(ApplicationLayerTest):

	@WithSharedApplicationMockDS
	def test_recover_user_logged_in( self ):
		with mock_dataserver.mock_db_trans(self.ds):
			_ = self._create_user( )

		app = TestApp( self.app )

		path = b'/dataserver2/logon.forgot.passcode'
		data = ""
		app.post( path, data, extra_environ=self._make_extra_environ(), status=403 )

	@WithSharedApplicationMockDS
	def test_recover_user_no_email( self ):
		app = TestApp( self.app )

		path = b'/dataserver2/logon.forgot.passcode'
		data = {}
		app.post( path, data, status=400 )

		mailer = component.getUtility( ITestMailDelivery )
		assert_that( mailer.queue, has_length( 0 ) )

	@WithSharedApplicationMockDS
	def test_recover_user_no_username( self ):
		app = TestApp( self.app )

		path = b'/dataserver2/logon.forgot.passcode'
		data = {'email': 'foo@bar.com'}
		res = app.post( path, data, status=400 )
		assert_that( res.body, contains_string( "Must provide username" ) )

	@WithSharedApplicationMockDS
	def test_recover_user_no_success( self ):
		app = TestApp( self.app )

		path = b'/dataserver2/logon.forgot.passcode'
		data = {'email': 'foo@bar.com', 'username': 'foo@bar.com' }
		res = app.post( path, data, status=400 )

		assert_that( res.body, contains_string( "Must provide success" ) )

	@WithSharedApplicationMockDS
	def test_recover_user_invalid_email( self ):
		app = TestApp( self.app )

		path = b'/dataserver2/logon.forgot.passcode'
		data = {'email': 'not valid'}
		res = app.post( path, data, status=422 )
		assert_that( res.json_body, has_entry( 'code', 'EmailAddressInvalid' ) )

		mailer = component.getUtility( ITestMailDelivery )
		assert_that( mailer.queue, has_length( 0 ) )

	@WithSharedApplicationMockDS
	def test_recover_user_not_found( self ):
		app = TestApp( self.app )

		path = b'/dataserver2/logon.forgot.passcode'
		data = {'email': 'not.registered@example.com', 'username': 'somebodyelse', 'success': 'http://localhost/place'}
		app.post( path, data, status=204 )

		mailer = component.getUtility( ITestMailDelivery )
		assert_that( mailer.queue, has_length( 1 ) )

	@WithSharedApplicationMockDS
	def test_recover_user_found( self ):
		with mock_dataserver.mock_db_trans(self.ds):
			user = self._create_user( )
			username = user.username
			profile = user_interfaces.IUserProfile( user )
			added( profile )
			profile.email = 'jason.madden@nextthought.com'
			modified( user )


		app = TestApp( self.app )

		path = b'/dataserver2/logon.forgot.passcode'
		data = {'email': 'jason.madden@nextthought.com',
				'username': username,
				'success': 'http://localhost/place'}
		app.post( path, data, status=204 )

		mailer = component.getUtility( ITestMailDelivery )
		assert_that( mailer.queue, has_length( 1 ) )
		msg = mailer.queue[0]

		assert_that( msg, has_property( 'body' ) )
		assert_that(decodestring(msg.body), 
                    contains_string( 'http://localhost/place?username=' + urllib_parse.quote(username) ) )

	@WithSharedApplicationMockDS
	def test_recover_user_found_multiple_matches( self ):
		with mock_dataserver.mock_db_trans(self.ds):
			user = self._create_user( )
			interface.alsoProvides( user, nti_interfaces.ICoppaUserWithoutAgreement )
			username = user.username
			profile = user_interfaces.IRestrictedUserProfileWithContactEmail( user )
			profile.email = 'jason.madden@nextthought.com'
			profile.contact_email = 'other.user@nextthought.com'
			modified( user )

		app = TestApp( self.app )

		# Find it via an actual email match
		path = b'/dataserver2/logon.forgot.passcode'
		data = {'email': 'jason.madden@nextthought.com',
				'username': username,
				'success': 'http://localhost/place'}
		__traceback_info__ = data
		app.post( path, data, status=204 )

		def _check_mail():
			mailer = component.getUtility( ITestMailDelivery )
			assert_that( mailer.queue, has_length( 1 ) )
			msg = mailer.queue[0]
			assert_that( msg, has_property( 'body' ) )
			assert_that( decodestring(msg.body), 
                         contains_string( 'http://localhost/place?username=' + urllib_parse.quote(username) ) )
			del mailer.queue[:]

		_check_mail()

		# Find it via a contact email match
		data = {'email': 'other.user@nextthought.com',
				'username': username,
				'success': 'http://localhost/place'}
		__traceback_info__ = data
		app.post( path, data, status=204 )
		_check_mail()

		# If we pass in an inconsistent case for the email, we still find it
		data = {'email': 'JASON.madden@nextthought.com',
				'username': username,
				'success': 'http://localhost/place'}
		__traceback_info__ = data
		app.post( path, data, status=204 )
		_check_mail()

		# Likewise for the contact email
		data = {'email': 'other.USER@nextthought.com',
				'username': username,
				'success': 'http://localhost/place'}
		__traceback_info__ = data
		app.post( path, data, status=204 )
		_check_mail()

		# And for the username too
		data = {'email': 'JASON.madden@nextthought.com',
				'username': username.upper(),
				'success': 'http://localhost/place'}
		__traceback_info__ = data
		app.post( path, data, status=204 )
		_check_mail()


	@WithSharedApplicationMockDS
	def test_recover_user_found_query_in_url( self ):
		with mock_dataserver.mock_db_trans(self.ds):
			user = self._create_user( )
			username = user.username
			profile = user_interfaces.IUserProfile( user )
			profile.email = 'jason.madden@nextthought.com'
			modified( user )

		app = TestApp( self.app )

		path = b'/dataserver2/logon.forgot.passcode'
		data = {'email': 'jason.madden@nextthought.com',
				'username': username,
				'success': 'http://localhost/place?host=foo&baz=bar'}
		app.post( path, data, status=204 )

		mailer = component.getUtility( ITestMailDelivery )
		assert_that( mailer.queue, has_length( 1 ) )
		msg = mailer.queue[0]
		assert_that( msg, has_property( 'body' ) )
		assert_that( decodestring(msg.body),
                     contains_string( 'http://localhost/place?host=foo&baz=bar&username=' + urllib_parse.quote(username) ) )

from zope.annotation.interfaces import IAnnotations
from nti.appserver import account_recovery_views
import datetime

class TestApplicationPasswordReset(ApplicationLayerTest):

	@WithSharedApplicationMockDS
	def test_reset_user_logged_in( self ):
		with mock_dataserver.mock_db_trans(self.ds):
			_ = self._create_user( )

		app = TestApp( self.app )

		path = b'/dataserver2/logon.reset.passcode'
		data = ""
		app.post( path, data, extra_environ=self._make_extra_environ(), status=403 )

	@WithSharedApplicationMockDS
	def test_reset_user_no_params( self ):
		app = TestApp( self.app )

		path = b'/dataserver2/logon.reset.passcode'
		data = {}
		app.post( path, data, status=400 )


	@WithSharedApplicationMockDS
	def test_recover_user_no_id( self ):
		app = TestApp( self.app )

		path = b'/dataserver2/logon.reset.passcode'
		data = {'username': 'not valid'}
		_ = app.post( path, data, status=400 )

	@WithSharedApplicationMockDS
	def test_recover_user_not_found( self ):
		app = TestApp( self.app )

		path = b'/dataserver2/logon.reset.passcode'
		data = {'id': 'not.registered@example.com', 'username': 'somebodyelse', }
		app.post( path, data, status=404 )

	@WithSharedApplicationMockDS
	def test_recover_user_found_with_data( self ):
		with mock_dataserver.mock_db_trans(self.ds):
			user = self._create_user( )
			username = user.username
			profile = user_interfaces.IUserProfile( user )
			profile.email = 'jason.madden@nextthought.com'
			IAnnotations(user)[account_recovery_views._KEY_PASSCODE_RESET] = ('the_id', datetime.datetime.utcnow())

		app = TestApp( self.app )

		path = b'/dataserver2/logon.reset.passcode'
		data = {'id': 'the_id',
				'username': username,
				'password': 'my_new_pwd'}
		app.post( path, data, status=200 )

		with mock_dataserver.mock_db_trans(self.ds):
			user = self._get_user()
			user.password.checkPassword( 'my_new_pwd' )

	@WithSharedApplicationMockDS
	def test_recover_user_found_with_data_bad_pwd( self ):
		with mock_dataserver.mock_db_trans(self.ds):
			user = self._create_user( )
			username = user.username
			profile = user_interfaces.IUserProfile( user )
			profile.email = 'jason.madden@nextthought.com'
			IAnnotations(user)[account_recovery_views._KEY_PASSCODE_RESET] = ('the_id', datetime.datetime.utcnow())

		app = TestApp( self.app )

		path = b'/dataserver2/logon.reset.passcode'

		data = {'id': 'the_id',
				'username': username }

		app.post( path, data, status=204 ) # preflights

		data['password'] = ' '
		app.post( path, data, status=422 )

		data['password'] = 'temp001'
		app.post( path, data )

		# And the annotation key is now gone
		with mock_dataserver.mock_db_trans( self.ds ):
			user = users.User.get_user( username )
			annotations = IAnnotations( user )
			assert_that( annotations, does_not( has_key( account_recovery_views._KEY_PASSCODE_RESET ) ) )
