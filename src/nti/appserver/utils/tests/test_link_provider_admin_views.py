#!/usr/bin/env python
from __future__ import print_function

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import json

from zope.annotation import IAnnotations

from nti.appserver import logon
from nti.appserver.link_providers import link_provider

from nti.dataserver import users
from nti.dataserver.tests import mock_dataserver
from nti.dataserver.dicts import LastModifiedDict

from nti.appserver.tests.test_application import TestApp
from nti.appserver.tests.test_application import SharedApplicationTestBase, WithSharedApplicationMockDS

from hamcrest import (assert_that, has_entry)

class TestLinkProviderAdminViews(SharedApplicationTestBase):

	@WithSharedApplicationMockDS
	def test_reset_initial_tos_page(self):

		with mock_dataserver.mock_db_trans(self.ds):
			user = self._create_user()
			link_dict = IAnnotations(user).get(link_provider._GENERATION_LINK_KEY)
			if link_dict is None:
				link_dict = LastModifiedDict()
				link_dict[logon.REL_INITIAL_TOS_PAGE] = '20130501'
				IAnnotations(user)[link_provider._GENERATION_LINK_KEY] = link_dict

		testapp = TestApp(self.app)
		testapp.post('/dataserver2/@@reset_initial_tos_page',
					 json.dumps({'username': 'sjohnson@nextthought.com'}),
					 extra_environ=self._make_extra_environ(),
					 status=204)

		with mock_dataserver.mock_db_trans(self.ds):
			user = users.User.get_user('sjohnson@nextthought.com')
			link_dict = IAnnotations(user).get(link_provider._GENERATION_LINK_KEY)
			assert_that(link_dict, has_entry(logon.REL_INITIAL_TOS_PAGE, ''))
