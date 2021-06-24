#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904
from contextlib import contextmanager

import fudge

from hamcrest import assert_that
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import contains_string
from hamcrest import has_property
from hamcrest import is_not as does_not
from hamcrest import has_key
from hamcrest import starts_with

from pyramid.request import Request

from quopri import decodestring

from six.moves import urllib_parse

from zope import component
from zope import interface

from zope.annotation import IAttributeAnnotatable

from zope.lifecycleevent import modified, added

from nti.app.testing.webtest import TestApp

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.appserver.account_recovery_views import UserAccountRecoveryUtility

from nti.appserver.interfaces import IApplicationSettings

from nti.appserver.policies.interfaces import IRequireSetPassword

from nti.dataserver.tests import mock_dataserver

from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver import users

from nti.dataserver.tests.mock_dataserver import DataserverLayerTest

from nti.dataserver.users import interfaces as user_interfaces

from nti.dataserver.users.common import set_user_creation_site

from nti.appserver.tests import ITestMailDelivery

_unset = object()


class _RecoveryTestBase(ApplicationLayerTest):

	def _add_user(self, email, username=None, site_name=None):
		with mock_dataserver.mock_db_trans(self.ds):
			user = self._create_user(username=username)
			username = user.username
			profile = user_interfaces.IUserProfile(user)
			added(profile)
			profile.email = email
			if site_name is not None:
				set_user_creation_site(user, site_name)
			modified(user)

		return username


class TestApplicationUsernameRecovery(_RecoveryTestBase):

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
		data = {'email': u'not.registered@example.com'}
		app.post( path, data, status=204 )

		mailer = component.getUtility( ITestMailDelivery )
		assert_that( mailer.queue, has_length( 1 ) )

	@WithSharedApplicationMockDS
	def test_recover_user_not_found_wrong_site(self):
		self._add_user(username=u"non_admin",
					   email=u'jason.madden@nextthought.com',
					   site_name=u'different_site')
		app = TestApp(self.app)

		path = b'/dataserver2/logon.forgot.username'
		data = {'email': u'jason.madden@nextthought.com'}
		extra_env = {'HTTP_ORIGIN': 'http://mathcounts.dev'}
		app.post(path, data, extra_environ=extra_env, status=204)

		mailer = component.getUtility(ITestMailDelivery)
		assert_that(mailer.queue, has_length(1))
		msg = mailer.queue[0]

		assert_that(msg, has_property('body'))
		assert_that(decodestring(msg.body),
					contains_string('No usernames were found'))

	@WithSharedApplicationMockDS
	@fudge.patch('nti.appserver.account_recovery_views._site_policy')
	def test_recover_user_not_found_alt_template(self, site_policy):
		# Ensure the proper template is found when no user is found and
		# the policy has specified a template in a folder
		fake_policy = fudge.Fake('SitePolicy')
		fake_policy.has_attr(
			USERNAME_RECOVERY_EMAIL_TEMPLATE_BASE_NAME='templates/username_recovery_email',
		)
		site_policy.is_callable().returns(fake_policy)
		app = TestApp(self.app)

		path = b'/dataserver2/logon.forgot.username'
		data = {'email': u'not.registered@example.com'}
		app.post(path, data, status=204)

		mailer = component.getUtility(ITestMailDelivery)
		assert_that(mailer.queue, has_length(1))
		msg = mailer.queue[0]

		assert_that(msg, has_property('body'))
		assert_that(decodestring(msg.body),
					contains_string('No usernames were found'))

	@WithSharedApplicationMockDS
	def test_recover_user_found_in_site(self):
		username = self._add_user(username=u"non_admin",
								  email=u'jason.madden@nextthought.com',
								  site_name=u'mathcounts.nextthought.com')

		app = TestApp(self.app)

		path = b'/dataserver2/logon.forgot.username'
		data = {'email': u'jason.madden@nextthought.com',}
		extra_env = {'HTTP_ORIGIN': 'http://mathcounts.dev'}
		app.post(path, data, extra_environ=extra_env, status=204)

		mailer = component.getUtility(ITestMailDelivery)
		assert_that(mailer.queue, has_length(1))
		msg = mailer.queue[0]

		assert_that(msg, has_property('body'))
		assert_that( decodestring(msg.body), contains_string( username ) )

	@WithSharedApplicationMockDS
	def test_recover_user_found_no_site( self ):
		user_username = self._add_user(username=u"non_admin",
									   email=u'jason.madden@nextthought.com',
									   site_name=None)

		app = TestApp( self.app )

		path = b'/dataserver2/logon.forgot.username'
		data = {'email': u'jason.madden@nextthought.com'}
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
			profile.email = u'jason.madden@nextthought.com'
			modified( user )

			user2 = self._create_user( username='other.user@foo.bar' )
			user2_username = user2.username
			profile = user_interfaces.IUserProfile( user2 )
			added( profile )
			profile.email = u'jason.madden@nextthought.com'
			modified( user2 )


		app = TestApp( self.app )

		path = b'/dataserver2/logon.forgot.username'
		data = {'email': u'jason.madden@nextthought.com'}
		app.post( path, data, status=204 )

		mailer = component.getUtility( ITestMailDelivery )
		assert_that( mailer.queue, has_length( 1 ) )
		msg = mailer.queue[0]

		assert_that( msg, has_property( 'body' ) )
		assert_that( decodestring(msg.body), contains_string( user_username ) )
		assert_that( decodestring(msg.body), contains_string( user2_username ) )


class TestApplicationPasswordRecovery(_RecoveryTestBase):

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
		data = {'email': u'foo@bar.com'}
		res = app.post( path, data, status=400 )
		assert_that( res.body, contains_string( "Must provide username" ) )

	@WithSharedApplicationMockDS
	def test_recover_user_no_success( self ):
		app = TestApp( self.app )

		path = b'/dataserver2/logon.forgot.passcode'
		data = {'email': u'foo@bar.com', 'username': 'foo@bar.com' }
		res = app.post( path, data, status=400 )

		assert_that( res.body, contains_string( "Must provide success" ) )

	@WithSharedApplicationMockDS
	def test_recover_user_invalid_email( self ):
		app = TestApp( self.app )

		path = b'/dataserver2/logon.forgot.passcode'
		data = {'email': u'not valid'}
		res = app.post( path, data, status=422 )
		assert_that( res.json_body, has_entry( 'code', 'EmailAddressInvalid' ) )

		mailer = component.getUtility( ITestMailDelivery )
		assert_that( mailer.queue, has_length( 0 ) )

	@WithSharedApplicationMockDS
	def test_recover_user_not_found( self ):
		app = TestApp( self.app )

		path = b'/dataserver2/logon.forgot.passcode'
		data = {'email': u'not.registered@example.com', 'username': 'somebodyelse', 'success': 'http://localhost/place'}
		app.post( path, data, status=204 )

		mailer = component.getUtility( ITestMailDelivery )
		assert_that( mailer.queue, has_length( 1 ) )

	@WithSharedApplicationMockDS
	@fudge.patch('nti.appserver.account_recovery_views._site_policy')
	def test_recover_user_not_found_alt_template(self, site_policy):
		# Ensure the proper template is found when no user is found and
		# the policy has specified a template in a folder
		fake_policy = fudge.Fake('SitePolicy')
		fake_policy.has_attr(
			PASSWORD_RESET_EMAIL_TEMPLATE_BASE_NAME='templates/password_reset_email',
		)
		site_policy.is_callable().returns(fake_policy)
		app = TestApp( self.app )

		path = b'/dataserver2/logon.forgot.passcode'
		data = {'email': u'not.registered@example.com', 'username': 'somebodyelse', 'success': 'http://localhost/place'}
		app.post( path, data, status=204 )

		mailer = component.getUtility( ITestMailDelivery )
		assert_that( mailer.queue, has_length( 1 ) )
		msg = mailer.queue[0]

		assert_that(msg, has_property('body'))
		assert_that(decodestring(msg.body),
					contains_string('the reset failed'))


	@WithSharedApplicationMockDS
	def test_recover_user_not_found_wrong_site( self ):
		username = self._add_user(username=u"non_admin",
								  email=u'jason.madden@nextthought.com',
								  site_name=u'different_site')
		app = TestApp( self.app )

		path = b'/dataserver2/logon.forgot.passcode'
		data = {'email': u'jason.madden@nextthought.com',
				'username': username,
				'success': 'http://localhost/place'}
		extra_env = {'HTTP_ORIGIN': 'http://mathcounts.dev'}
		app.post(path, data, extra_environ=extra_env, status=204)

		mailer = component.getUtility( ITestMailDelivery )
		assert_that( mailer.queue, has_length( 1 ) )
		msg = mailer.queue[0]

		assert_that(msg, has_property('body'))
		assert_that(decodestring(msg.body),
					contains_string('reset failed'))

	@WithSharedApplicationMockDS
	def test_recover_user_found_in_site(self):
		username = self._add_user(username=u"non_admin",
								  email=u'jason.madden@nextthought.com',
								  site_name=u'mathcounts.nextthought.com')

		app = TestApp(self.app)

		path = b'/dataserver2/logon.forgot.passcode'
		data = {'email': u'jason.madden@nextthought.com',
				'username': username,
				'success': 'http://localhost/place'}
		extra_env = {'HTTP_ORIGIN': 'http://mathcounts.dev'}
		app.post(path, data, extra_environ=extra_env, status=204)

		mailer = component.getUtility(ITestMailDelivery)
		assert_that(mailer.queue, has_length(1))
		msg = mailer.queue[0]

		assert_that(msg, has_property('body'))
		assert_that(decodestring(msg.body),
					contains_string('http://localhost/place?username=' + urllib_parse.quote(username)))

	@WithSharedApplicationMockDS
	def test_recover_user_found_no_site( self ):
		username = self._add_user(username=u"non_admin",
								  email=u'jason.madden@nextthought.com',
								  site_name=None)

		app = TestApp( self.app )

		path = b'/dataserver2/logon.forgot.passcode'
		data = {'email': u'jason.madden@nextthought.com',
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
			profile.email = u'jason.madden@nextthought.com'
			profile.contact_email = u'other.user@nextthought.com'
			modified( user )

		app = TestApp( self.app )

		# Find it via an actual email match
		path = b'/dataserver2/logon.forgot.passcode'
		data = {'email': u'jason.madden@nextthought.com',
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
		data = {'email': u'other.user@nextthought.com',
				'username': username,
				'success': 'http://localhost/place'}
		__traceback_info__ = data
		app.post( path, data, status=204 )
		_check_mail()

		# If we pass in an inconsistent case for the email, we still find it
		data = {'email': u'JASON.madden@nextthought.com',
				'username': username,
				'success': 'http://localhost/place'}
		__traceback_info__ = data
		app.post( path, data, status=204 )
		_check_mail()

		# Likewise for the contact email
		data = {'email': u'other.USER@nextthought.com',
				'username': username,
				'success': 'http://localhost/place'}
		__traceback_info__ = data
		app.post( path, data, status=204 )
		_check_mail()

		# And for the username too
		data = {'email': u'JASON.madden@nextthought.com',
				'username': username.upper(),
				'success': 'http://localhost/place'}
		__traceback_info__ = data
		app.post( path, data, status=204 )
		_check_mail()


	@WithSharedApplicationMockDS
	def test_recover_user_found_query_in_url( self ):
		username = self._add_user(email=u'jason.madden@nextthought.com')

		app = TestApp( self.app )

		path = b'/dataserver2/logon.forgot.passcode'
		data = {'email': u'jason.madden@nextthought.com',
				'username': username,
				'success': 'http://localhost/place?host=foo&baz=bar'}
		app.post( path, data, status=204 )

		mailer = component.getUtility( ITestMailDelivery )
		assert_that( mailer.queue, has_length( 1 ) )
		msg = mailer.queue[0]
		assert_that( msg, has_property( 'body' ) )
		decoded_body = decodestring(msg.body)
		assert_that(decoded_body,
					contains_string( 'http://localhost/place?host=foo&baz=bar&username=' + urllib_parse.quote(username) ))
		assert_that(decoded_body,
					contains_string(''))

	@WithSharedApplicationMockDS
	@fudge.patch('nti.appserver.account_recovery_views._site_brand')
	def test_branded_subject( self, get_site_brand ):
		get_site_brand.is_callable().returns("Brand XYZ")
		username = self._add_user(email=u'jason.madden@nextthought.com')

		app = TestApp( self.app )

		path = b'/dataserver2/logon.forgot.passcode'
		data = {'email': u'jason.madden@nextthought.com',
				'username': username,
				'success': 'http://localhost/place?host=foo&baz=bar'}
		app.post( path, data, status=204 )

		mailer = component.getUtility( ITestMailDelivery )
		assert_that( mailer.queue, has_length( 1 ) )
		subject = mailer.queue[0].subject
		assert_that(subject,
					contains_string('Brand XYZ Password Reset'))

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

	def _set_reset_code(self, user, token_id, age=None):
		token_creation_time = (datetime.datetime.utcnow() if age is None
							   else datetime.datetime.utcnow() - age)
		IAnnotations(user)[account_recovery_views._KEY_PASSCODE_RESET] = \
			code = (token_id, token_creation_time)
		return code

	@WithSharedApplicationMockDS
	def test_expired_link( self ):
		with mock_dataserver.mock_db_trans(self.ds):
			user = self._create_user()
			username = user.username
			self._set_reset_code(user,
								 'the_id',
								 age=datetime.timedelta(hours=5))

		app = TestApp( self.app )

		path = b'/dataserver2/logon.reset.passcode'
		data = {'id': 'the_id', 'username': username, }
		res = app.post( path, data, status=404 )
		json_body = res.json_body

		assert_that(json_body,
					has_entry('code',
							  'InvalidOrMissingOrExpiredResetToken'))

	@WithSharedApplicationMockDS
	def test_extended_expiry( self ):
		"""
		Users marked with IRequireSetPassword and that have no password set
		should have extended expiration
		"""
		# Initially set creation time to just over 7 days, which should fail
		with mock_dataserver.mock_db_trans(self.ds):
			user = self._create_user(password=None)
			interface.alsoProvides(user, IRequireSetPassword)
			username = user.username
			self._set_reset_code(user,
								 'the_id',
								 age=datetime.timedelta(days=7, seconds=1))

		app = TestApp( self.app )

		path = b'/dataserver2/logon.reset.passcode'
		data = {'id': 'the_id',
				'username': username,
				'password': 'my_new_pwd'}
		res = app.post( path, data, status=404 )
		json_body = res.json_body

		assert_that(json_body,
					has_entry('code',
							  'InvalidOrMissingOrExpiredResetToken'))

		# Just under 7 days should succeed
		with mock_dataserver.mock_db_trans(self.ds):
			user = self._get_user(username)
			self._set_reset_code(user,
								 'the_id',
								 age=datetime.timedelta(days=6, hours=23))

		res = app.post( path, data, status=200 )

	@WithSharedApplicationMockDS
	def test_require_no_pass_for_extended_expiry( self ):
		"""
		Users with a password get shorter expiry, even if marked with
		IRequireSetPassword (currently, this shouldn't occur)
		"""
		with mock_dataserver.mock_db_trans(self.ds):
			user = self._create_user()
			interface.alsoProvides(user, IRequireSetPassword)
			username = user.username
			IAnnotations(user)[account_recovery_views._KEY_PASSCODE_RESET] = \
				('the_id', datetime.datetime.utcnow() - datetime.timedelta(hours=5))

		app = TestApp( self.app )

		path = b'/dataserver2/logon.reset.passcode'
		data = {'id': 'the_id', 'username': username, }
		res = app.post( path, data, status=404 )
		json_body = res.json_body

		assert_that(json_body,
					has_entry('code',
							  'InvalidOrMissingOrExpiredResetToken'))


	@WithSharedApplicationMockDS
	def test_recover_user_found_with_data( self ):
		with mock_dataserver.mock_db_trans(self.ds):
			user = self._create_user( )
			username = user.username
			profile = user_interfaces.IUserProfile( user )
			profile.email = u'jason.madden@nextthought.com'
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
			profile.email = u'jason.madden@nextthought.com'
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


class TestAccountRecoveryUtility(DataserverLayerTest):

	def _query_params(self, url):
		url_parts = list(urllib_parse.urlparse(url))
		return dict(urllib_parse.parse_qsl(url_parts[4]))

	@staticmethod
	def _run_FUT(app_url, request_path, settings):
		util = UserAccountRecoveryUtility()
		user = fudge.Fake('User').has_attr(username='test_user')
		interface.alsoProvides(user, IAttributeAnnotatable)

		request = Request.blank(request_path, base_url=app_url)

		with _provide_utility(settings, IApplicationSettings):
			url = util.get_password_reset_url(user, request)

		return url

	def test_success_param(self):
		app_url = 'https://nti.com'
		base_success_url = 'https://nti.com/reset/?existing_param=abc'
		success_param = urllib_parse.quote_plus(base_success_url)
		request_path = '/path/?success=%s' % success_param
		settings = dict(password_reset_url='/login/recover/reset')

		url = self._run_FUT(app_url, request_path, settings)

		assert_that(url, starts_with("%s&username" % base_success_url))

	def test_url_from_application_url(self):
		app_url = 'https://nti.com'
		request_path = '/path/'

		url = self._run_FUT(app_url, request_path, {})

		assert_that(url, starts_with("https://nti.com?username"))

	def test_url_from_settings(self):
		app_url = "https://nti.com"
		request_path = '/path/'
		settings = dict(password_reset_url='/login/recover/reset')

		url = self._run_FUT(app_url, request_path, settings)

		assert_that(url, starts_with("https://nti.com/login/recover/reset?username"))


@contextmanager
def _provide_utility(util, iface):
	gsm = component.getGlobalSiteManager()

	old_util = component.queryUtility(iface)
	gsm.registerUtility(util, iface)
	try:
		yield
	finally:
		gsm.unregisterUtility(util, iface)
		gsm.registerUtility(old_util, iface)
