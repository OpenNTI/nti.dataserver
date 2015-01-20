#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import has_entry
from hamcrest import assert_that

from nti.app.users.mail_views import get_verification_token_data
from nti.app.users.mail_views import generate_mail_verification_token

from nti.dataserver.users.interfaces import IUserProfile

from nti.dataserver.tests import mock_dataserver

from nti.app.testing.decorators import WithSharedApplicationMockDS
from nti.app.testing.application_webtest import ApplicationLayerTest

class TestMailViews(ApplicationLayerTest):

	@WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=True)
	def test_generate_mail_verification_token(self):
		
		with mock_dataserver.mock_db_trans( self.ds ):
			user = self._create_user(username="ichigo" )
			IUserProfile(user).email = "ichigo@bleach.org"
			
			# generate token
			token = generate_mail_verification_token(user, timestamp=1)
			assert_that( token, is_not(none()))
			
			data = get_verification_token_data(user, token)
			assert_that(data, has_entry('timestamp', is_(1)))
			assert_that(data, has_entry('username', is_('ichigo')))
			assert_that(data, has_entry('email', is_('ichigo@bleach.org')))