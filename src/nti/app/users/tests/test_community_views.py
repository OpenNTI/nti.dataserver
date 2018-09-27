#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods,too-many-function-args

from hamcrest import is_
from hamcrest import is_in
from hamcrest import is_not
from hamcrest import contains
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_property
from nti.testing.time import time_monotonically_increases

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.coremetadata.interfaces import ISiteCommunity

from nti.dataserver.contenttypes.note import Note

from nti.dataserver.tests import mock_dataserver

from nti.dataserver.users.communities import Community

from nti.dataserver.users.interfaces import IHiddenMembership

from nti.dataserver.users.users import User


class TestCommunityViews(ApplicationLayerTest):

    @WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=True)
    def test_create_list_community(self):
        ext_obj = {'username': 'bleach',
                   'alias': 'Bleach',
                   'realname': 'Bleach',
                   'public': True,
                   'joinable': True}
        path = '/dataserver2/@@create_community'
        res = self.testapp.post_json(path, ext_obj, status=201)
        assert_that(res.json_body, has_entry('Username', 'bleach'))
        assert_that(res.json_body, has_entry('alias', 'Bleach'))
        assert_that(res.json_body, has_entry('realname', 'Bleach'))
        with mock_dataserver.mock_db_trans(self.ds):
            c = Community.get_community(username='bleach')
            assert_that(c, has_property('public', is_(True)))
            assert_that(c, has_property('joinable', is_(True)))
            assert_that(ISiteCommunity.providedBy(c), is_(False))

        path = '/dataserver2/@@list_communities'
        res = self.testapp.get(path, status=200)
        assert_that(res.json_body, has_entry('Items', has_length(2)))
        assert_that(res.json_body, has_entry('Total', is_(2)))

        path = '/dataserver2/@@list_communities'
        params = {
            "searchTerm": 'B',
            "mimeTypes": 'application/vnd.nextthought.community'
        }
        res = self.testapp.get(path, params, status=200)
        assert_that(res.json_body, has_entry('Items', has_length(1)))
        assert_that(res.json_body, has_entry('Total', is_(1)))

        # Site community
        ext_obj = {'username': 'bleach_site_community',
                   'alias': 'Bleach',
                   'realname': 'Bleach',
                   'public': True,
                   'joinable': True,
                   'is_site_community': True}
        path = '/dataserver2/@@create_community'
        res = self.testapp.post_json(path, ext_obj, status=201)
        assert_that(res.json_body, has_entry('Username', 'bleach_site_community'))
        with mock_dataserver.mock_db_trans(self.ds):
            c = Community.get_community(username='bleach_site_community')
            assert_that(c, has_property('public', is_(True)))
            assert_that(c, has_property('joinable', is_(True)))
            assert_that(ISiteCommunity.providedBy(c), is_(True))


    @WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=True)
    def test_update_community(self):
        with mock_dataserver.mock_db_trans(self.ds):
            c = Community.create_community(username=u'bleach')
            assert_that(c, has_property('public', is_(False)))
            assert_that(c, has_property('joinable', is_(False)))

        ext_obj = {'alias': 'Bleach',
                   'realname': 'Bleach',
                   'public': True,
                   'joinable': True}
        path = '/dataserver2/users/bleach'

        res = self.testapp.put_json(path, ext_obj,
                                    status=200,
                                    extra_environ=self._make_extra_environ(user=self.default_username))
        assert_that(res.json_body, has_entry('Username', 'bleach'))
        assert_that(res.json_body, has_entry('alias', 'Bleach'))
        assert_that(res.json_body, has_entry('realname', 'Bleach'))
        with mock_dataserver.mock_db_trans(self.ds):
            c = Community.get_community(username=u'bleach')
            assert_that(c, has_property('public', is_(True)))
            assert_that(c, has_property('joinable', is_(True)))

    @WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=True)
    def test_get_community(self):
        with mock_dataserver.mock_db_trans(self.ds):
            Community.create_community(username=u'bleach')
            self._create_user(u"ichigo", u"temp001")

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
            Community.create_community(username=u'bleach')

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

    @time_monotonically_increases(60)
    @WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=True)
    def test_membership_community(self):
        with mock_dataserver.mock_db_trans(self.ds):
            c = Community.create_community(username=u'bleach')
            user = User.get_user(self.default_username)
            user.record_dynamic_membership(c)
            user = self._create_user(u"ichigo", u"temp001")
            user.record_dynamic_membership(c)
            self._create_user(u"aizen", u"temp001")

        path = '/dataserver2/users/bleach/members'
        res = self.testapp.get(path, status=200)
        assert_that(res.json_body, has_entry('Items', has_length(2)))

        path = '/dataserver2/users/bleach/members?sortOn=createdTime&sortOrder=descending'
        res = self.testapp.get(path, status=200)
        assert_that(res.json_body, has_entry('Items', contains(has_entry('Username', 'ichigo'),
                                                               has_entry('Username', self.default_username.lower()))))

        path = '/dataserver2/users/bleach/members?sortOn=createdTime&sortOrder=ascending'
        res = self.testapp.get(path, status=200)
        assert_that(res.json_body, has_entry('Items', contains(has_entry('Username', self.default_username.lower()),
                                                               has_entry('Username', 'ichigo'))))

        res = self.testapp.get(path,
                               extra_environ=self._make_extra_environ(user="ichigo"),
                               status=200)
        assert_that(res.json_body, has_entry('Items', has_length(2)))

        self.testapp.get(path,
                         extra_environ=self._make_extra_environ(user="aizen"),
                         status=403)

        hide_path = '/dataserver2/users/bleach/hide'
        self.testapp.post(hide_path, status=200)

        res = self.testapp.get(path,
                               extra_environ=self._make_extra_environ(user="ichigo"),
                               status=200)
        assert_that(res.json_body, has_entry('Items', has_length(1)))

        with mock_dataserver.mock_db_trans(self.ds):
            community = Community.get_community(username='bleach')
            user = User.get_user(self.default_username)
            hidden = IHiddenMembership(community)
            assert_that(user, is_in(hidden))
            assert_that(list(hidden.iter_intids()), has_length(1))

        unhide_path = '/dataserver2/users/bleach/unhide'
        self.testapp.post(unhide_path, status=200)

        res = self.testapp.get(path,
                               extra_environ=self._make_extra_environ(user="ichigo"),
                               status=200)
        assert_that(res.json_body, has_entry('Items', has_length(2)))

    @WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=True)
    def test_activity_community(self):
        with mock_dataserver.mock_db_trans(self.ds):
            c = Community.create_community(username=u'bleach')
            user = User.get_user(self.default_username)
            user.record_dynamic_membership(c)
            user = self._create_user(u"ichigo", u"temp001")
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
