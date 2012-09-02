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
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import contains_string
from hamcrest import has_property

from nti.dataserver.users import interfaces as user_interfaces


from zope import component

from pyramid_mailer.interfaces import IMailer
import urllib

from .test_application import ApplicationTestBase
from webtest import TestApp
from nti.dataserver.tests import mock_dataserver


class TestApplicationUsernameRecovery(ApplicationTestBase):

	def test_recover_user_logged_in( self ):
		with mock_dataserver.mock_db_trans(self.ds):
			_ = self._create_user( )

		app = TestApp( self.app )

		path = b'/dataserver2/logon.forgot.username'
		data = ""
		app.post( path, data, extra_environ=self._make_extra_environ(), status=403 )

	def test_recover_user_no_email( self ):
		app = TestApp( self.app )

		path = b'/dataserver2/logon.forgot.username'
		data = {}
		app.post( path, data, status=400 )

		mailer = component.getUtility( IMailer )
		assert_that( mailer.outbox, has_length( 0 ) )

	def test_recover_user_invalid_email( self ):
		app = TestApp( self.app )

		path = b'/dataserver2/logon.forgot.username'
		data = {'email': 'not valid'}
		res = app.post( path, data, status=422 )
		assert_that( res.json_body, has_entry( 'code', 'EmailAddressInvalid' ) )


		mailer = component.getUtility( IMailer )
		assert_that( mailer.outbox, has_length( 0 ) )


	def test_recover_user_not_found( self ):
		app = TestApp( self.app )

		path = b'/dataserver2/logon.forgot.username'
		data = {'email': 'not.registered@example.com'}
		app.post( path, data, status=204 )

		mailer = component.getUtility( IMailer )
		assert_that( mailer.outbox, has_length( 1 ) )

	def test_recover_user_found( self ):
		with mock_dataserver.mock_db_trans(self.ds):
			user = self._create_user( )
			profile = user_interfaces.IUserProfile( user )
			profile.email = 'jason.madden@nextthought.com'

		app = TestApp( self.app )

		path = b'/dataserver2/logon.forgot.username'
		data = {'email': 'jason.madden@nextthought.com'}
		app.post( path, data, status=204 )

		mailer = component.getUtility( IMailer )
		assert_that( mailer.outbox, has_length( 1 ) )
		msg = mailer.outbox[0]
		assert_that( msg, has_property( 'body', contains_string( user.username ) ) )


class TestApplicationPasswordRecovery(ApplicationTestBase):

	def test_recover_user_logged_in( self ):
		with mock_dataserver.mock_db_trans(self.ds):
			_ = self._create_user( )

		app = TestApp( self.app )

		path = b'/dataserver2/logon.forgot.passcode'
		data = ""
		app.post( path, data, extra_environ=self._make_extra_environ(), status=403 )

	def test_recover_user_no_email( self ):
		app = TestApp( self.app )

		path = b'/dataserver2/logon.forgot.passcode'
		data = {}
		app.post( path, data, status=400 )

		mailer = component.getUtility( IMailer )
		assert_that( mailer.outbox, has_length( 0 ) )

	def test_recover_user_invalid_email( self ):
		app = TestApp( self.app )

		path = b'/dataserver2/logon.forgot.passcode'
		data = {'email': 'not valid'}
		res = app.post( path, data, status=422 )
		assert_that( res.json_body, has_entry( 'code', 'EmailAddressInvalid' ) )


		mailer = component.getUtility( IMailer )
		assert_that( mailer.outbox, has_length( 0 ) )


	def test_recover_user_not_found( self ):
		app = TestApp( self.app )

		path = b'/dataserver2/logon.forgot.passcode'
		data = {'email': 'not.registered@example.com', 'username': 'somebodyelse', 'success': 'http://localhost/place'}
		app.post( path, data, status=204 )

		mailer = component.getUtility( IMailer )
		assert_that( mailer.outbox, has_length( 1 ) )

	def test_recover_user_found( self ):
		with mock_dataserver.mock_db_trans(self.ds):
			user = self._create_user( )
			profile = user_interfaces.IUserProfile( user )
			profile.email = 'jason.madden@nextthought.com'

		app = TestApp( self.app )

		path = b'/dataserver2/logon.forgot.passcode'
		data = {'email': 'jason.madden@nextthought.com',
				'username': user.username,
				'success': 'http://localhost/place'}
		app.post( path, data, status=204 )

		mailer = component.getUtility( IMailer )
		assert_that( mailer.outbox, has_length( 1 ) )
		msg = mailer.outbox[0]

		assert_that( msg, has_property( 'body', contains_string( 'http://localhost/place?username=' + urllib.quote(user.username) ) ) )

from zope.annotation.interfaces import IAnnotations
from nti.appserver import account_recovery_views
import datetime

class TestApplicationPasswordReset(ApplicationTestBase):

	def test_reset_user_logged_in( self ):
		with mock_dataserver.mock_db_trans(self.ds):
			_ = self._create_user( )

		app = TestApp( self.app )

		path = b'/dataserver2/logon.reset.passcode'
		data = ""
		app.post( path, data, extra_environ=self._make_extra_environ(), status=403 )

	def test_reset_user_no_params( self ):
		app = TestApp( self.app )

		path = b'/dataserver2/logon.reset.passcode'
		data = {}
		app.post( path, data, status=400 )


	def test_recover_user_no_id( self ):
		app = TestApp( self.app )

		path = b'/dataserver2/logon.reset.passcode'
		data = {'username': 'not valid'}
		_ = app.post( path, data, status=400 )

	def test_recover_user_not_found( self ):
		app = TestApp( self.app )

		path = b'/dataserver2/logon.reset.passcode'
		data = {'id': 'not.registered@example.com', 'username': 'somebodyelse', }
		app.post( path, data, status=404 )


	def test_recover_user_found_with_data( self ):
		with mock_dataserver.mock_db_trans(self.ds):
			user = self._create_user( )
			profile = user_interfaces.IUserProfile( user )
			profile.email = 'jason.madden@nextthought.com'
			IAnnotations(user)[account_recovery_views._KEY_PASSCODE_RESET] = ('the_id', datetime.datetime.utcnow())

		app = TestApp( self.app )

		path = b'/dataserver2/logon.reset.passcode'
		data = {'id': 'the_id',
				'username': user.username,
				'password': 'my_new_pwd'}
		app.post( path, data, status=200 )

		with mock_dataserver.mock_db_trans(self.ds):
			user.password.checkPassword( 'my_new_pwd' )
