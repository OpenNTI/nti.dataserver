#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import has_item
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import greater_than
from hamcrest import has_property

import fudge

from zope import interface
from zope import component
from zope import lifecycleevent

from zope.intid.interfaces import IIntIds

from nti.app.users import VIEW_USER_UPSERT
from nti.app.users import VIEW_GRANT_USER_ACCESS
from nti.app.users import VIEW_RESTRICT_USER_ACCESS

from nti.app.users.utils import get_user_creation_sitename

from nti.dataserver.contenttypes.note import Note

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IAccessProvider

from nti.dataserver.users.index import get_entity_catalog

from nti.dataserver.users.interfaces import IUserProfile

from nti.dataserver.users.users import User

from nti.dataserver.users.utils import is_email_verified

from nti.site.hostpolicy import get_all_host_sites

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.dataserver.tests import mock_dataserver

from nti.externalization.externalization import StandardExternalFields

from nti.ntiids.oids import to_external_ntiid_oid

ITEMS = StandardExternalFields.ITEMS


@component.adapter(IUser)
@interface.implementer(IAccessProvider)
class AlwaysPassUserAccessProvider(object):

    def __init__(self, *args):
        pass

    def grant_access(self, *args, **kwargs):
        pass

    def remove_access(self, *args, **kwargs):
        pass


class TestAdminViews(ApplicationLayerTest):

    def setUp(self):
        super(TestAdminViews, self).setUp()
        component.getGlobalSiteManager().registerAdapter(AlwaysPassUserAccessProvider,
                                                         (IUser,),
                                                         IAccessProvider)

    def tearDown(self):
        super(TestAdminViews, self).tearDown()
        component.getGlobalSiteManager().unregisterAdapter(AlwaysPassUserAccessProvider)

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


    def _get_workspace(self, name):
        service_doc = '/dataserver2/service'
        res = self.testapp.get(service_doc)
        res = res.json_body
        result = next(x for x in res[ITEMS] if x['Title'] == name)
        return result

    @WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=True)
    def test_user_update(self):
        global_workspace = self._get_workspace(u'Global')
        catalog_workspace = self._get_workspace(u'Catalog')
        username = u'ed_brubaker'
        username2 = u'ed_brubaker_duplicate'
        external_type = u'employee id'
        external_id = u'1112345'
        with mock_dataserver.mock_db_trans(self.ds):
            user = self._create_user(username)
            self._create_user(username2)
            catalog = get_entity_catalog()
            intids = component.getUtility(IIntIds)
            doc_id = intids.getId(user)
            catalog.index_doc(doc_id, user)
            user_ntiid = to_external_ntiid_oid(user)
            invalid_access_ntiid = to_external_ntiid_oid(user.__parent__)

        # Set external ids via admin view
        admin_external_href = '/dataserver2/users/%s/%s' % (username, 'LinkUserExternalIdentity')
        self.testapp.post_json(admin_external_href, {'external_type': external_type,
                                                     'external_id': external_id})
        # Cannot map to different user
        admin_external_href = '/dataserver2/users/%s/%s' % (username2, 'LinkUserExternalIdentity')
        self.testapp.post_json(admin_external_href, {'external_type': external_type,
                                                     'external_id': external_id},
                               status=422)

        user1_environ = self._make_extra_environ(user=username)

        user_update_href = self.require_link_href_with_rel(global_workspace,
                                                           VIEW_USER_UPSERT)

        grant_access_href = self.require_link_href_with_rel(catalog_workspace,
                                                            VIEW_GRANT_USER_ACCESS)

        remove_access_href = self.require_link_href_with_rel(catalog_workspace,
                                                             VIEW_RESTRICT_USER_ACCESS)

        # Empty update succeeds
        user_update_href_username = '%s?username=%s' % (user_update_href, username)
        self.testapp.post_json(user_update_href_username)

        # Update user
        new_first = u'Ed'
        new_last = u'Brubaker'
        new_email = u'new_email@gmail.com'
        self.testapp.post_json(user_update_href, {u'first_name': new_first,
                                                  u'last_name': new_last,
                                                  u'external_type': external_type,
                                                  u'external_id': external_id,
                                                  u'email': new_email})
        res = self.testapp.get('/dataserver2/users/%s' % username,
                               extra_environ=user1_environ)
        res = res.json_body
        assert_that(res['realname'], is_('%s %s' % (new_first, new_last)))
        assert_that(res['email'], is_(new_email))

        # Create user
        new_first = u'Charlie'
        new_last = u'Parish'
        new_email = u'parish@gmail.com'
        new_external_id = '99999'
        new_external_type = 'employee id'
        res = self.testapp.post_json(user_update_href,
                                     {u'first_name': new_first,
                                      u'last_name': new_last,
                                      u'external_type': new_external_type,
                                      u'external_id': new_external_id,
                                      u'email': new_email})
        res = res.json_body
        created_username = res.get('Username')
        assert_that(created_username, is_not(new_email))

        with mock_dataserver.mock_db_trans(self.ds):
            user = User.get_user(created_username)
            user.password = 'temp001'
        user2_environ = self._make_extra_environ(user=created_username)

        res = self.testapp.get('/dataserver2/users/%s' % created_username,
                               extra_environ=user2_environ)
        res = res.json_body
        assert_that(res['realname'], is_('%s %s' % (new_first, new_last)))
        assert_that(res['email'], is_(new_email))

        # Granting/removing access
        full_data = {u'ntiid': user_ntiid,
                     u'external_type': new_external_type,
                     u'external_id': new_external_id}
        missing_access = {u'ntiid': u"does_not_exist_ntiid",
                          u'external_type': new_external_type,
                          u'external_id': new_external_id}
        invalid_access = {u'ntiid': invalid_access_ntiid,
                          u'external_type': new_external_type,
                          u'external_id': new_external_id}
        missing_user = {u'ntiid': user_ntiid,
                        u'external_type': u"does_not_exist_type",
                        u'external_id': new_external_id}
        missing_user2 = {u'ntiid': user_ntiid,
                        u'external_type': new_external_type,
                        u'external_id': u'does_not_exist_id'}
        self.testapp.post_json(grant_access_href, full_data)
        self.testapp.post_json(grant_access_href, invalid_access, status=422)
        self.testapp.post_json(grant_access_href, missing_access, status=404)
        self.testapp.post_json(grant_access_href, missing_user, status=404)
        self.testapp.post_json(grant_access_href, missing_user2, status=404)
        self.testapp.post_json(remove_access_href, full_data)
        self.testapp.post_json(remove_access_href, invalid_access, status=422)
        self.testapp.post_json(remove_access_href, missing_access, status=404)
        self.testapp.post_json(remove_access_href, missing_user, status=404)
        self.testapp.post_json(remove_access_href, missing_user2, status=404)

    @WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=True)
    @fudge.patch('nti.app.users.utils.is_site_admin',
                 'nti.app.users.utils.get_component_hierarchy_names',
                 'nti.app.users.utils.get_user_creation_sitename')
    def test_user_update_site_admin(self, mock_site_admin, mock_get_site_names, mock_get_user_site_name):
        """
        Validate site admins can only update users in their site.
        """
        mock_site_admin.is_callable().returns(True)
        mock_get_site_names.is_callable().returns(('test_site',))
        test_site_username = u'test_site_user'
        test_site_email = u'%s@gmail.com' % test_site_username
        external_type = u'employee id'
        external_id = u'1112345'

        with mock_dataserver.mock_db_trans(self.ds):
            user = self._create_user(test_site_username)
            IUserProfile(user).email = test_site_email
            catalog = get_entity_catalog()
            intids = component.getUtility(IIntIds)
            doc_id = intids.getId(user)
            catalog.index_doc(doc_id, user)
        admin_external_href = '/dataserver2/users/%s/%s' % (test_site_username,
                                                            'LinkUserExternalIdentity')
        self.testapp.post_json(admin_external_href, {'external_type': external_type,
                                                     'external_id': external_id})

        global_workspace = self._get_workspace(u'Global')
        user_update_href = self.require_link_href_with_rel(global_workspace,
                                                           VIEW_USER_UPSERT)

        fake_user_site = mock_get_user_site_name.is_callable().returns('test_site')
        fake_user_site.next_call().returns(object())
        fake_user_site.next_call().returns(None)

        user_update_href = '%s?external_type=%s&external_id=%s' % (user_update_href,
                                                                   external_type,
                                                                   external_id)

        self.testapp.post_json(user_update_href)
        self.testapp.post_json(user_update_href, status=403)
        self.testapp.post_json(user_update_href, status=403)
