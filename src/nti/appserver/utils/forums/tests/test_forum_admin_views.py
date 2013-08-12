#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from nti.dataserver import users
from nti.dataserver.contenttypes.forums.forum import CommunityForum
from nti.dataserver.contenttypes.forums import interfaces as frm_interfaces

from nti.externalization.externalization import to_json_representation

from nti.appserver.tests.test_application import TestApp

from nti.dataserver.tests import mock_dataserver
from nti.appserver.tests.test_application import SharedApplicationTestBase, WithSharedApplicationMockDS

from hamcrest import (assert_that, is_, has_length, none)

class TestForumAdminViews(SharedApplicationTestBase):

	features = SharedApplicationTestBase.features + ('forums',)

	@WithSharedApplicationMockDS
	def test_set_community_forum_acl(self):
		with mock_dataserver.mock_db_trans(self.ds):
			self._create_user()
			community = users.Community.create_community(self.ds, username='bleach')
			board = frm_interfaces.ICommunityBoard(community)
			board['bankai'] = CommunityForum()
			aizen = self._create_user(username='aizen@nt.com')
			aizen.record_dynamic_membership(community)

		testapp = TestApp(self.app)

		path = '/dataserver2/@@set_community_forum_acl'
		environ = self._make_extra_environ()
		data = to_json_representation({'community': 'bleach',
									   'ACL': [ {"Action": "Allow", 
												 "Class": "ForumACE", 
												 "Entities": ["aizen@nt.com"], 
												 "MimeType": "application/vnd.nextthought.forums.ace", 
												 "Permissions": ["All"] } ] })
		res = testapp.post(path, data, extra_environ=environ)
		assert_that(res.status_int, is_(204))

		with mock_dataserver.mock_db_trans(self.ds):
			comm = users.Community.get_community('bleach')
			board = frm_interfaces.ICommunityBoard(comm)
			forum = board.get('bankai')
			assert_that(frm_interfaces.IACLCommunityForum.providedBy(forum), is_(True))
			acl = getattr(forum, 'ACL', ())
			assert_that(acl, has_length(1))

	@WithSharedApplicationMockDS
	def test_set_community_board_acl(self):
		with mock_dataserver.mock_db_trans(self.ds):
			self._create_user()
			aizen = self._create_user(username='aizen@nt.com')
			ichigo = self._create_user(username='ichigo@nt.com')
			kuchiki = self._create_user(username='kuchiki@nt.com')

			comm = users.Community.create_community(self.ds, username='bleach')
			for user in (aizen, ichigo, kuchiki):
				user.record_dynamic_membership(comm)

		testapp = TestApp(self.app)

		path = '/dataserver2/@@set_community_board_acl'
		environ = self._make_extra_environ()
		data = to_json_representation({'community': 'bleach',
									   'ACL': [ {"Action": "Allow", 
												 "Class": "ForumACE", 
												 "Entities": ["aizen@nt.com"], 
												 "MimeType": "application/vnd.nextthought.forums.ace", 
												 "Permissions": ["All"] },
												{"Action": "Allow",
												 "Class": "ForumACE",
												 "Entities": ["ichigo@nt.com", 'kuchiki@nt.com'],
												 "MimeType": "application/vnd.nextthought.forums.ace",
												 "Permissions": ["All"] }
											   ] })
		res = testapp.post(path, data, extra_environ=environ)
		assert_that(res.status_int, is_(204))

		with mock_dataserver.mock_db_trans(self.ds):
			comm = users.Community.get_community('bleach')
			board = frm_interfaces.ICommunityBoard(comm)
			assert_that(frm_interfaces.IACLCommunityBoard.providedBy(board), is_(True))

			acl = getattr(board, 'ACL', None)
			assert_that(acl, has_length(2))

	@WithSharedApplicationMockDS
	def test_delete_community_forum(self):
		with mock_dataserver.mock_db_trans(self.ds):
			self._create_user()
			community = users.Community.create_community(self.ds, username='bleach')
			board = frm_interfaces.ICommunityBoard(community)
			board['bankai'] = CommunityForum()
		testapp = TestApp(self.app)

		path = '/dataserver2/@@delete_community_forum'
		environ = self._make_extra_environ()
		data = to_json_representation({'community': 'bleach', 'forum':'bankai'})
		res = testapp.post(path, data, extra_environ=environ)
		assert_that(res.status_int, is_(204))

		with mock_dataserver.mock_db_trans(self.ds):
			comm = users.Community.get_community('bleach')
			board = frm_interfaces.ICommunityBoard(comm)
			forum = board.get('bankai')
			assert_that(forum, is_(none()))

