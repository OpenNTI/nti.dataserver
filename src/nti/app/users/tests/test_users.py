#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import raises
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import only_contains
from hamcrest import calling

from zope import component
from zope import lifecycleevent
from zope import interface

from nti.dataserver.interfaces import IDataserver
from nti.dataserver.users.interfaces import BlacklistedUsernameError
from nti.dataserver.users.interfaces import IRecreatableUser

from nti.dataserver.users import User

from nti.app.testing.application_webtest import ApplicationLayerTest
from nti.app.testing.decorators import WithSharedApplicationMockDSWithChanges
from nti.dataserver.tests import mock_dataserver

class TestUsers(ApplicationLayerTest):

	@WithSharedApplicationMockDSWithChanges
	def test_user_blacklist(self):
		username = 'lazarus'
		with mock_dataserver.mock_db_trans( self.ds ):
			# Create user
			dataserver = component.getUtility( IDataserver )
			ds_folder = dataserver.dataserver_folder

			blacklist_folder = ds_folder['++etc++username_blacklist']
			assert_that( blacklist_folder, has_length( 0 ) )
			user_one = User.create_user( username=username )

		with mock_dataserver.mock_db_trans(self.ds):
			# Remove user
			lifecycleevent.removed( user_one )

			dataserver = component.getUtility( IDataserver )
			ds_folder = dataserver.dataserver_folder

			blacklist_folder = ds_folder['++etc++username_blacklist']
			assert_that( blacklist_folder._storage, only_contains( username ) )

		with mock_dataserver.mock_db_trans(self.ds):
			# Same name
			assert_that( calling( User.create_user ).with_args( username=username ),
						raises( BlacklistedUsernameError ))

		with mock_dataserver.mock_db_trans(self.ds):
			# Now case insensitive
			assert_that( calling( User.create_user ).with_args( username=username.upper() ),
						raises( BlacklistedUsernameError ))

	@WithSharedApplicationMockDSWithChanges
	def test_recreate(self):
		username = 'lazarus'
		with mock_dataserver.mock_db_trans( self.ds ):
			# Create user
			user_one = User.create_user( username=username )
			interface.alsoProvides( user_one, IRecreatableUser )

		with mock_dataserver.mock_db_trans(self.ds):
			# Remove user that is not blacklisted
			User.delete_user(username)

			dataserver = component.getUtility( IDataserver )
			ds_folder = dataserver.dataserver_folder
			blacklist_folder = ds_folder['++etc++username_blacklist']
			assert_that( blacklist_folder, has_length( 0 ) )

		with mock_dataserver.mock_db_trans( self.ds ):
			# Recreate user, no problem
			dataserver = component.getUtility( IDataserver )
			ds_folder = dataserver.dataserver_folder
			user_one = User.create_user( username=username )
