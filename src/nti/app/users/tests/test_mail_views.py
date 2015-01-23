#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import has_entry
from hamcrest import assert_that
from hamcrest import has_property
from hamcrest import contains_string

from nti.app.users.mail_views import generate_mail_verification_pair
from nti.app.users.mail_views import get_verification_signature_data
from nti.app.users.mail_views import generate_verification_email_url

from nti.dataserver.users import User
from nti.dataserver.users.interfaces import IUserProfile
from nti.dataserver.users.utils import is_email_verified

from nti.dataserver.tests import mock_dataserver

from nti.app.testing.decorators import WithSharedApplicationMockDS
from nti.app.testing.application_webtest import ApplicationLayerTest

class TestMailViews(ApplicationLayerTest):

	@WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=True)
	def test_generate_mail_verification_token(self):
		
		with mock_dataserver.mock_db_trans( self.ds ):
			user = self._create_user(username="ichigo" )
			IUserProfile(user).email = "ichigo@bleach.org"
			
			signature, token = generate_mail_verification_pair(user, secret_key='zangetsu')		
			assert_that( token, is_(49114861L))
			assert_that( signature, contains_string('2mDfJ4TTqRAsSGcjhNiea13Q0GHPqC6yB_AZV8Jt__c'))
			
			data = get_verification_signature_data(user, signature, secret_key='zangetsu')
			assert_that(data, has_entry('username', is_('ichigo')))
			assert_that(data, has_entry('email', is_('ichigo@bleach.org')))
			
	@WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=True)
	def test_verify_user_email_with_token(self):
		username = 'ichigo@bleach.org'
		with mock_dataserver.mock_db_trans( self.ds ):
			user = User.create_user(username=username, password='temp001',
						 	 		external_value={ u'email':u"ichigo@bleach.org"})
			
			_, token = generate_mail_verification_pair(user)		
				
		post_data = {'token':token}
		path = '/dataserver2/@@verify_user_email_with_token'
		extra_environ = self._make_extra_environ(user=username)
		self.testapp.post_json(path, post_data, extra_environ=extra_environ, status=204)
		
		with mock_dataserver.mock_db_trans(self.ds):
			user = User.get_user(username)
			assert_that(IUserProfile(user), has_property('email_verified', is_(True)))
			assert_that(is_email_verified(username), is_(True))

	@WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=True)
	def test_verify_user_email_view(self):
		username = 'ichigo@bleach.org'
		with mock_dataserver.mock_db_trans( self.ds ):
			user = User.create_user(username=username, password='temp001',
						 	 		external_value={ u'email':u"ichigo@bleach.org"})
			
			href, _, = generate_verification_email_url(user)		
				
		extra_environ = self._make_extra_environ(user=username)
		self.testapp.get(href, extra_environ=extra_environ, status=204)
		
		with mock_dataserver.mock_db_trans(self.ds):
			user = User.get_user(username)
			assert_that(IUserProfile(user), has_property('email_verified', is_(True)))
			assert_that(is_email_verified(username), is_(True))
