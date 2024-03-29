#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import raises
from hamcrest import calling
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import only_contains

import time

from zope import component
from zope import interface
from zope import lifecycleevent

from zope.event import notify

from nti.app.users.subscribers import LAST_SEEN_UPDATE_BUFFER_IN_SEC

from nti.coremetadata.interfaces import UserLastSeenEvent

from nti.dataserver.interfaces import IDataserver

from nti.dataserver.users.communities import Community

from nti.dataserver.users.friends_lists import DynamicFriendsList

from nti.dataserver.users.interfaces import IRecreatableUser
from nti.dataserver.users.interfaces import BlacklistedUsernameError

from nti.dataserver.users.users import User

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS
from nti.app.testing.decorators import WithSharedApplicationMockDSWithChanges

from nti.app.testing.request_response import DummyRequest

from nti.dataserver.tests import mock_dataserver

from nti.ntiids.ntiids import find_object_with_ntiid


class TestUsers(ApplicationLayerTest):

    @WithSharedApplicationMockDSWithChanges
    def test_user_last_seen(self):
        username = u'herodotus_lastseen'
        request = DummyRequest()
        t0 = time.time()
        t0_thirty = t0 + 30
        t0_buffer_minus_one = t0 + LAST_SEEN_UPDATE_BUFFER_IN_SEC - 1
        t0_buffer_plus_one = t0 + LAST_SEEN_UPDATE_BUFFER_IN_SEC + 1
        with mock_dataserver.mock_db_trans(self.ds):
            user = User.create_user(username=username)
            notify(UserLastSeenEvent(user, t0, request))
            assert_that(user.lastSeenTime, is_(t0))
            for small_delta_time in (t0_thirty, t0_buffer_minus_one):
                notify(UserLastSeenEvent(user, small_delta_time, request))
                assert_that(user.lastSeenTime, is_(t0))
            notify(UserLastSeenEvent(user, t0_buffer_plus_one, request))
            assert_that(user.lastSeenTime, is_(t0_buffer_plus_one))

    @WithSharedApplicationMockDSWithChanges
    def test_user_blacklist(self):

        username = u'lazarus'
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
        username = u'lazarus'
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
    def test_memberships(self):

        with mock_dataserver.mock_db_trans(self.ds):
            c = Community.create_community(username=u'bleach')
            user = User.get_user(self.default_username)
            user.record_dynamic_membership(c)

            ichigo = self._create_user(u"ichigo", u"temp001")
            ichigo.record_dynamic_membership(c)

            aizen = self._create_user(u"aizen", u"temp001")
            aizen.record_dynamic_membership(c)

            self._create_user(u"rukia", "temp001")

            # Our DFL creator and member will now have 2 memberships.
            dfl = DynamicFriendsList(username=u'Friends')
            dfl.creator = ichigo
            ichigo.addContainedObject(dfl)
            dfl.addFriend(aizen)
            dfl_ntiid = dfl.NTIID

        path = '/dataserver2/users/%s/memberships' % self.default_username
        res = self.testapp.get(path, status=200)
        assert_that(res.json_body, has_entry('Items', has_length(1)))

        # Ichigo on sjohnson
        res = self.testapp.get(path,
                               extra_environ=self._make_extra_environ(user=u"ichigo"),
                               status=200)
        assert_that(res.json_body, has_entry('Items', has_length(1)))

        # DFL owner
        path = '/dataserver2/users/ichigo/memberships'
        res = self.testapp.get(path,
                               extra_environ=self._make_extra_environ(user=u"ichigo"),
                               status=200)
        assert_that(res.json_body, has_entry('Items', has_length(2)))

        # Member on owner returns the same
        res = self.testapp.get(path,
                               extra_environ=self._make_extra_environ(user=u"aizen"),
                               status=200)
        assert_that(res.json_body, has_entry('Items', has_length(2)))

        # Member
        path = '/dataserver2/users/aizen/memberships'
        res = self.testapp.get(path,
                               extra_environ=self._make_extra_environ(user=u"aizen"),
                               status=200)
        assert_that(res.json_body, has_entry('Items', has_length(2)))

        # Owner on the member sees it
        res = self.testapp.get(path,
                               extra_environ=self._make_extra_environ(user=u"ichigo"),
                               status=200)
        assert_that(res.json_body, has_entry('Items', has_length(2)))

        # Third party nothing
        res = self.testapp.get(path,
                               extra_environ=self._make_extra_environ(user=u"rukia"),
                               status=200)
        assert_that(res.json_body, has_entry('Items', has_length(0)))

        path = '/dataserver2/users/aizen/memberships'
        res = self.testapp.get(path,
                               extra_environ=self._make_extra_environ(user=u"rukia"),
                               status=200)
        assert_that(res.json_body, has_entry('Items', has_length(0)))

        # Delete dfl
        with mock_dataserver.mock_db_trans(self.ds):
            dfl = find_object_with_ntiid(dfl_ntiid)
            for user in dfl:
                dfl.removeFriend(user)

        self.testapp.delete('/dataserver2/Objects/%s' % dfl_ntiid,
                            extra_environ=self._make_extra_environ(user=u"ichigo"))
        path = '/dataserver2/users/ichigo/memberships'
        res = self.testapp.get(path,
                               extra_environ=self._make_extra_environ(user=u"ichigo"),
                               status=200)
        assert_that(res.json_body, has_entry('Items', has_length(1)))

        path = '/dataserver2/users/aizen/memberships'
        res = self.testapp.get(path,
                               extra_environ=self._make_extra_environ(user=u"aizen"),
                               status=200)
        assert_that(res.json_body, has_entry('Items', has_length(1)))

class TestAvatarViews(ApplicationLayerTest):

    @WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=False)
    def test_anonymously_accessible(self):

        user_env = self._make_extra_environ(user=self.default_username)
        path = '/dataserver2/users/%s/@@avatar' % self.default_username

        # Returns a 302 to the avatar
        self.testapp.get(path, status=302, extra_environ=user_env)

        # Can be fetched anonymously also
        self.testapp.get(path, status=302)
