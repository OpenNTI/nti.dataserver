#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import raises
from hamcrest import calling
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import only_contains

from zope import component
from zope import interface
from zope import lifecycleevent

from nti.dataserver.interfaces import IDataserver

from nti.dataserver.users import User
from nti.dataserver.users import Community
from nti.dataserver.users.interfaces import IRecreatableUser
from nti.dataserver.users.interfaces import BlacklistedUsernameError

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS
from nti.app.testing.decorators import WithSharedApplicationMockDSWithChanges

from nti.dataserver.tests import mock_dataserver

class TestUsers(ApplicationLayerTest):

	@WithSharedApplicationMockDSWithChanges
	def test_user_blacklist(self):
		username = 'lazarus'
		with mock_dataserver.mock_db_trans(self.ds):
			# Create user
			dataserver = component.getUtility(IDataserver)
			ds_folder = dataserver.dataserver_folder

			blacklist_folder = ds_folder['++etc++username_blacklist']
			assert_that(blacklist_folder, has_length(0))
			user_one = User.create_user(username=username)

		with mock_dataserver.mock_db_trans(self.ds):
			# Remove user
			lifecycleevent.removed(user_one)

			dataserver = component.getUtility(IDataserver)
			ds_folder = dataserver.dataserver_folder

			blacklist_folder = ds_folder['++etc++username_blacklist']
			assert_that(blacklist_folder._storage, only_contains(username))

		with mock_dataserver.mock_db_trans(self.ds):
			# Same name
			assert_that(calling(User.create_user).with_args(username=username),
						raises(BlacklistedUsernameError))

		with mock_dataserver.mock_db_trans(self.ds):
			# Now case insensitive
			assert_that(calling(User.create_user).with_args(username=username.upper()),
						raises(BlacklistedUsernameError))

	@WithSharedApplicationMockDSWithChanges
	def test_recreate(self):
		username = 'lazarus'
		with mock_dataserver.mock_db_trans(self.ds):
			# Create user
			user_one = User.create_user(username=username)
			interface.alsoProvides(user_one, IRecreatableUser)

		with mock_dataserver.mock_db_trans(self.ds):
			# Remove user that is not blacklisted
			User.delete_user(username)

			dataserver = component.getUtility(IDataserver)
			ds_folder = dataserver.dataserver_folder
			blacklist_folder = ds_folder['++etc++username_blacklist']
			assert_that(blacklist_folder, has_length(0))

		with mock_dataserver.mock_db_trans(self.ds):
			# Recreate user, no problem
			dataserver = component.getUtility(IDataserver)
			ds_folder = dataserver.dataserver_folder
			user_one = User.create_user(username=username)

	@WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=True)
	def test_membership_community(self):
		with mock_dataserver.mock_db_trans(self.ds):
			c = Community.create_community(username='bleach')
			user = User.get_user(self.default_username)
			user.record_dynamic_membership(c)
			
			ichigo = self._create_user("ichigo", "temp001")
			ichigo.record_dynamic_membership(c)
			
			aizen = self._create_user("aizen", "temp001")
			aizen.record_dynamic_membership(c)
			
			self._create_user("rukia", "temp001")

		path = '/dataserver2/users/%s/memberships' % self.default_username
		res = self.testapp.get(path, status=200)
		assert_that(res.json_body, has_entry('Items', has_length(1)))
		
		res = self.testapp.get(	path, 
					  			extra_environ=self._make_extra_environ(user="ichigo"),
					  			status=200)
		assert_that(res.json_body, has_entry('Items', has_length(1)))

		path = '/dataserver2/users/aizen/memberships'
		res = self.testapp.get(path, 
					  		   extra_environ=self._make_extra_environ(user="aizen"),
					  	 	   status=200)
		assert_that(res.json_body, has_entry('Items', has_length(1)))
		
		path = '/dataserver2/users/aizen/memberships'
		res = self.testapp.get(path, 
					  	 	   extra_environ=self._make_extra_environ(user="rukia"),
					  	 	   status=200)
		assert_that(res.json_body, has_entry('Items', has_length(0)))
