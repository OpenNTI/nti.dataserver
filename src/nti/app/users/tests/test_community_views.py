
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import is_in
from hamcrest import is_not
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_property

from nti.dataserver.users import User
from nti.dataserver.users import Community
from nti.dataserver.contenttypes import Note
from nti.dataserver.users.interfaces import IHiddenMembership

from nti.dataserver.tests import mock_dataserver

from nti.app.testing.decorators import WithSharedApplicationMockDS
from nti.app.testing.application_webtest import ApplicationLayerTest

class TestCommunityViews(ApplicationLayerTest):

	@WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=True)
	def test_create_list_community(self):
		ext_obj = {'username': 'bleach',
 				   'alias': 'Bleach',
 				   'realname': u'Bleach',
 				   'public': True,
 				   'joinable': True}
		path = '/dataserver2/@@create_community'
		res = self.testapp.post_json(path, ext_obj, status=200)
		assert_that(res.json_body, has_entry('Username', 'bleach'))
		assert_that(res.json_body, has_entry('alias', 'Bleach'))
		assert_that(res.json_body, has_entry('realname', 'Bleach'))
		with mock_dataserver.mock_db_trans(self.ds):
			c = Community.get_community(username='bleach')
			assert_that(c, has_property('public', is_(True)))
			assert_that(c, has_property('joinable', is_(True)))

		path = '/dataserver2/@@list_communities'
		res = self.testapp.get(path, status=200)
		assert_that(res.json_body, has_entry('Items', has_length(2)))
		assert_that(res.json_body, has_entry('Total', is_(2)))

		path = '/dataserver2/@@list_communities?term=B'
		res = self.testapp.get(path, status=200)
		assert_that(res.json_body, has_entry('Items', has_length(1)))
		assert_that(res.json_body, has_entry('Total', is_(1)))

	@WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=True)
	def test_update_community(self):
		with mock_dataserver.mock_db_trans(self.ds):
			c = Community.create_community(username='bleach')
			assert_that(c, has_property('public', is_(False)))
			assert_that(c, has_property('joinable', is_(False)))

		ext_obj = {'alias': 'Bleach',
 				   'realname': u'Bleach',
 				   'public': True,
 				   'joinable': True}
		path = '/dataserver2/users/bleach'

		res = self.testapp.put_json(path, ext_obj, status=200,
									extra_environ=self._make_extra_environ(user=self.default_username))
		assert_that(res.json_body, has_entry('Username', 'bleach'))
		assert_that(res.json_body, has_entry('alias', 'Bleach'))
		assert_that(res.json_body, has_entry('realname', 'Bleach'))
		with mock_dataserver.mock_db_trans(self.ds):
			c = Community.get_community(username='bleach')
			assert_that(c, has_property('public', is_(True)))
			assert_that(c, has_property('joinable', is_(True)))

	@WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=True)
	def test_get_community(self):
		with mock_dataserver.mock_db_trans(self.ds):
			Community.create_community(username='bleach')
			self._create_user("ichigo", "temp001")

		path = '/dataserver2/users/bleach'
		self.testapp.get(path,
					  	 extra_environ=self._make_extra_environ(user="ichigo"),
					  	 status=403)

		with mock_dataserver.mock_db_trans(self.ds):
			c = Community.get_community(username='bleach')
			c.public = True

		self.testapp.get(path,
					  	 extra_environ=self._make_extra_environ(user="ichigo"),
					  	 status=200)

	@WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=True)
	def test_join_community(self):
		with mock_dataserver.mock_db_trans(self.ds):
			Community.create_community(username='bleach')

		path = '/dataserver2/users/bleach/join'
		self.testapp.post(path, status=403)

		with mock_dataserver.mock_db_trans(self.ds):
			c = Community.get_community(username='bleach')
			c.joinable = True

		self.testapp.post(path, status=200)
		with mock_dataserver.mock_db_trans(self.ds):
			community = Community.get_community(username='bleach')
			user = User.get_user(self.default_username)
			assert_that(user, is_in(community))

	@WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=True)
	def test_leave_community(self):
		with mock_dataserver.mock_db_trans(self.ds):
			c = Community.create_community(username='bleach')
			c.joinable = True
			user = User.get_user(self.default_username)
			user.record_dynamic_membership(c)

		path = '/dataserver2/users/bleach/leave'
		self.testapp.post(path, status=200)
		with mock_dataserver.mock_db_trans(self.ds):
			community = Community.get_community(username='bleach')
			user = User.get_user(self.default_username)
			assert_that(user, is_not(is_in(community)))

	@WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=True)
	def test_membership_community(self):
		with mock_dataserver.mock_db_trans(self.ds):
			c = Community.create_community(username='bleach')
			user = User.get_user(self.default_username)
			user.record_dynamic_membership(c)
			user = self._create_user("ichigo", "temp001")
			user.record_dynamic_membership(c)
			self._create_user("aizen", "temp001")

		path = '/dataserver2/users/bleach/members'
		res = self.testapp.get(path, status=200)
		assert_that(res.json_body, has_entry('Items', has_length(2)))

		res = self.testapp.get(	path,
					  			extra_environ=self._make_extra_environ(user="ichigo"),
					  			status=200)
		assert_that(res.json_body, has_entry('Items', has_length(2)))

		self.testapp.get(path,
					  	 extra_environ=self._make_extra_environ(user="aizen"),
					  	 status=403)

		hide_path = '/dataserver2/users/bleach/hide'
		self.testapp.post(hide_path, status=200)

		res = self.testapp.get(	path,
					  			extra_environ=self._make_extra_environ(user="ichigo"),
					  			status=200)
		assert_that(res.json_body, has_entry('Items', has_length(1)))

		with mock_dataserver.mock_db_trans(self.ds):
			community = Community.get_community(username='bleach')
			user = User.get_user(self.default_username)
			hidden = IHiddenMembership(community)
			assert_that(user, is_in(hidden))

		unhide_path = '/dataserver2/users/bleach/unhide'
		self.testapp.post(unhide_path, status=200)

		res = self.testapp.get(	path,
					  			extra_environ=self._make_extra_environ(user="ichigo"),
					  			status=200)
		assert_that(res.json_body, has_entry('Items', has_length(2)))

	@WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=True)
	def test_activity_community(self):
		with mock_dataserver.mock_db_trans(self.ds):
			c = Community.create_community(username='bleach')
			user = User.get_user(self.default_username)
			user.record_dynamic_membership(c)
			user = self._create_user("ichigo", "temp001")
			user.record_dynamic_membership(c)

			note = Note()
			note.body = [u'bankai']
			note.creator = user
			note.addSharingTarget(c)
			note.containerId = u'mycontainer'
			user.addContainedObject(note)

		path = '/dataserver2/users/bleach/Activity'
		res = self.testapp.get(path, status=200)
		assert_that(res.json_body, has_entry('Items', has_length(1)))
