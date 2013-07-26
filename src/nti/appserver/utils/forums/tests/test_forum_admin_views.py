#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904


import simplejson
from datetime import date

from zope import interface

from nti.appserver import site_policies
from nti.appserver.link_providers import flag_link_provider

from nti.dataserver import users
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.users import interfaces as users_interfaces
from nti.dataserver.contenttypes.forums import interfaces as frm_interfaces

from nti.externalization.externalization import to_json_representation

from nti.appserver.tests.test_application import TestApp

from nti.dataserver.tests import mock_dataserver
from nti.appserver.tests.test_application import SharedApplicationTestBase, WithSharedApplicationMockDS

from hamcrest import (assert_that, is_, has_length, has_entry, has_key)

class TestForumAdminViews(SharedApplicationTestBase):

	features = SharedApplicationTestBase.features + ('forums',)

	@WithSharedApplicationMockDS
	def test_set_class_community_forum(self):
		with mock_dataserver.mock_db_trans(self.ds):
			self._create_user()
			aizen = self._create_user(username='aizen@nt.com')
			ichigo = self._create_user(username='ichigo@nt.com')
			kuchiki = self._create_user(username='kuchiki@nt.com')

			comm = users.Community.create_community(self.ds, username='bleach')
			for user in (aizen, ichigo, kuchiki):
				user.join_community(comm)

		return
		testapp = TestApp(self.app)

		path = '/dataserver2/@@set_class_community_forum'
		environ = self._make_extra_environ()
		data = to_json_representation({'community': 'bleach',
									   'sharedWith': ['aizen@nt.com', 'ichigo@nt.com', 'kuchiki@nt.com'] })
		
		res = testapp.post(path, data, extra_environ=environ)
		assert_that(res.status_int, is_(200))

		with mock_dataserver.mock_db_trans(self.ds):
			comm = users.Community.get_community('bleach')
			forum = frm_interfaces.ICommunityForum(comm)
			assert_that(frm_interfaces.IClassForum.providedBy(forum), is_(True))
			assert_that(frm_interfaces.ICommunityForum.providedBy(forum), is_(True))
