#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import has_item
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import greater_than
from hamcrest import has_property

from zope import lifecycleevent

from nti.app.users.utils import get_user_creation_sitename

from nti.dataserver.contenttypes import Note

from nti.dataserver.users import User

from nti.dataserver.users.interfaces import IUserProfile

from nti.dataserver.users.utils import is_email_verified

from nti.site.hostpolicy import get_all_host_sites

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.dataserver.tests import mock_dataserver


class TestAdminViews(ApplicationLayerTest):

    @WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=True)
    def test_blacklist_views(self):
        username = u'user_one'
        # Baseline
        path = '/dataserver2/GetUserBlacklist'
        res = self.testapp.get(path, None, status=200)
        body = res.json_body
        assert_that(body, has_entry('Items', has_length(0)))
        assert_that(body, has_entry('Total', is_(0)))

        with mock_dataserver.mock_db_trans(self.ds):
            # Remove user
            user_one = User.create_user(username=username)
            lifecycleevent.removed(user_one)

        # Ok user is in our blacklist
        res = self.testapp.get(path, None, status=200)
        body = res.json_body
        assert_that(body, has_entry('Items', has_length(1)))
        assert_that(body, has_entry('Items', has_item(username)))
        assert_that(body, has_entry('Total', is_(1)))

        # Undo
        self.testapp.post_json('/dataserver2/RemoveFromUserBlacklist',
                               {'username': username},
                               status=200)

        # Blacklist is empty
        res = self.testapp.get(path, None, status=200)
        body = res.json_body
        assert_that(body, has_entry('Items', has_length(0)))
        assert_that(body, has_entry('Total', is_(0)))

        with mock_dataserver.mock_db_trans(self.ds):
            user_one = User.create_user(username=u'ichigo')
            lifecycleevent.removed(user_one)

        res = self.testapp.get(path, None, status=200)
        assert_that(res.json_body, has_entry('Items', has_length(1)))

        self.testapp.post_json('/dataserver2/@@ResetUserBlacklist',
                               status=204)

        res = self.testapp.get(path, None, status=200)
        assert_that(res.json_body, has_entry('Items', has_length(0)))

    @WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=True)
    def test_force_email_verification(self):
        username = u'user_one'
        email = u'user.one@foo.com'
        with mock_dataserver.mock_db_trans(self.ds):
            user = User.create_user(username=username,
                                    external_value={u'email': email})
            assert_that(IUserProfile(user), 
                        has_property('email_verified', is_(False)))
            assert_that(is_email_verified(username), is_(False))

        self.testapp.post_json('/dataserver2/@@ForceUserEmailVerification',
                               {'username': username},
                               status=204)

        with mock_dataserver.mock_db_trans(self.ds):
            user = User.get_user(username=username)
            assert_that(IUserProfile(user), has_property('email', is_(email)))
            assert_that(IUserProfile(user), 
                        has_property('email_verified', is_(True)))
            assert_that(is_email_verified(email), is_(True))
            
    @WithSharedApplicationMockDS(users=True, testapp=True)
    def test_rebuild_entity_catalog(self):
        res = self.testapp.post('/dataserver2/@@RebuildEntityCatalog',
                                status=200)
        assert_that(res.json_body, 
                    has_entry('Total', is_(greater_than(1))))

    @WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=True)
    def test_get_email_verification_token(self):
        username = u'user_one'
        email = u'user.one@foo.com'
        with mock_dataserver.mock_db_trans(self.ds):
            User.create_user(username=username,
                             external_value={u'email': email})

        res = self.testapp.get('/dataserver2/@@GetEmailVerificationToken',
                               {'username': username},
                               status=200)

        assert_that(res.json_body, has_entry('Signature', has_length(132)))
        assert_that(res.json_body, has_entry('Token', is_(int)))

    @WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=True)
    def test_set_user_creation_site(self):
        username = u'ichigo'
        with mock_dataserver.mock_db_trans(self.ds):
            User.create_user(username=username)
            sites = list(get_all_host_sites())
            sitename = sites[0].__name__ if sites else 'dataserver2'

        self.testapp.post_json('/dataserver2/@@SetUserCreationSite',
                               {'username': username, 'site':'invalid_site'},
                               status=422)

        self.testapp.post_json('/dataserver2/@@SetUserCreationSite',
                               {'username': username, 'site':sitename},
                               status=204)
        
        with mock_dataserver.mock_db_trans(self.ds):
            creation_site = get_user_creation_sitename(username)
            if sitename != 'dataserver2':
                assert_that(creation_site, is_(sitename))

    @WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=True)
    def test_remove_user(self):
        username = u'user_one'

        with mock_dataserver.mock_db_trans(self.ds):
            user = User.get_user(username=username)
            assert_that(user, is_(none()))

        with mock_dataserver.mock_db_trans(self.ds):
            User.create_user(username=username)

        self.testapp.post_json('/dataserver2/@@RemoveUser',
                               {'username': username},
                               status=204)

        with mock_dataserver.mock_db_trans(self.ds):
            user = User.get_user(username=username)
            assert_that(user, is_(none()))

        self.testapp.post_json('/dataserver2/@@RemoveUser',
                               {'username': username},
                               status=422)

    @WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=True)
    def test_ghost_objects(self):
        username = self.default_username.lower()
        with mock_dataserver.mock_db_trans(self.ds):
            user = User.get_user(username)
            note = Note()
            note.body = [u'bankai']
            note.creator = user
            note.containerId = u'mycontainer'
            note = user.addContainedObject(note)

        path = '/dataserver2/@@GhostContainers'
        params = {"usernames": username}
        res = self.testapp.get(path, params, status=200)
        assert_that(res.json_body, has_entry('Total', is_(1)))
        assert_that(res.json_body,
                    has_entry('Items',
                              has_entry(username, has_length(1))))
        
        path = '/dataserver2/@@RemoveGhostContainers'
        res = self.testapp.post_json(path, params, status=200)
        assert_that(res.json_body, has_entry('Total', is_(1)))
        assert_that(res.json_body,
                    has_entry('Items',
                              has_entry(username, has_length(1))))
        
        path = '/dataserver2/@@GhostContainers'
        res = self.testapp.get(path, params, status=200)
        assert_that(res.json_body,
                    has_entry('Items',
                              has_entry(username, has_length(0))))
