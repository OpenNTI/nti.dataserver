#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods,too-many-function-args

from hamcrest import is_
from hamcrest import none
from hamcrest import is_in
from hamcrest import is_not
from hamcrest import not_none
from hamcrest import contains
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_entries
from hamcrest import has_property
from hamcrest import contains_inanyorder
does_not = is_not

from nti.testing.time import time_monotonically_increases

from zope import interface

from zope.component.hooks import getSite

from zope.securitypolicy.interfaces import IPrincipalRoleManager

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.app.users.utils import get_entity_creation_sitename

from nti.coremetadata.interfaces import ISiteCommunity

from nti.dataserver.authorization import ROLE_SITE_ADMIN_NAME

from nti.dataserver.contenttypes.note import Note

from nti.dataserver.tests import mock_dataserver

from nti.dataserver.users.auto_subscribe import SiteAutoSubscribeMembershipPredicate

from nti.dataserver.users.common import entity_creation_sitename
from nti.dataserver.users.common import set_entity_creation_site

from nti.dataserver.users.communities import Community

from nti.dataserver.users.interfaces import IHiddenMembership

from nti.dataserver.users.users import User


class TestCommunityViews(ApplicationLayerTest):

    default_origin = 'https://alpha.nextthought.com'

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
            creation_site = entity_creation_sitename(c)
            assert_that(creation_site, is_('alpha.nextthought.com'))

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
            creation_site = entity_creation_sitename(c)
            assert_that(creation_site, is_('alpha.nextthought.com'))

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

    @WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=True)
    def test_community_admin(self):
        self.default_origin = 'https://alpha.nextthought.com'
        # XXX: If you do not specify a site the permissions will be set on `dataserver2`
        # this will cause users to have unexpected permissions as the ds folder is always
        # in the lineage whereas the host policy folder is not
        with mock_dataserver.mock_db_trans(self.ds, site_name='alpha.nextthought.com'):
            c = Community.create_community(username=u'mycommunity')
            user = User.get_user(self.default_username)
            user.record_dynamic_membership(c)
            user = self._create_user(u"sheldon", u"temp001", external_value={'realname': u'Sheldon Smith',
                                                                             'email': u'alpha@user.com'})
            user.record_dynamic_membership(c)
            self._create_user(u'siteadmin', u'temp001', external_value={'realname': u'Site Admin',
                                                                                    'email': u'admin@user.com'})
            site = getSite()
            prm = IPrincipalRoleManager(site)
            prm.assignRoleToPrincipal(ROLE_SITE_ADMIN_NAME, 'siteadmin')
            assert_that(c.is_admin(self.default_username), is_(False))
            assert_that(c.is_admin(u'sheldon'), is_(False))
            set_entity_creation_site(c, 'alpha.nextthought.com')

        path = '/dataserver2/users/mycommunity/%s'
        site_admin_env = self._make_extra_environ(u'siteadmin')
        basic_env = self._make_extra_environ(u'sheldon')

        # Site admin can admin the site community
        self.testapp.get(path % '',
                         extra_environ=site_admin_env)

        # Test site admin can access as community admin
        self.testapp.put_json(path % 'AddAdmin',
                              {'username': 'siteadmin'},
                              status=200)
        self.testapp.get(path % '',
                         status=200,
                         extra_environ=site_admin_env)

        # Test site admin can access as a non community admin community member
        self.testapp.put_json(path % 'RemoveAdmin',
                              {'username': 'siteadmin'},
                              status=200)
        with mock_dataserver.mock_db_trans(self.ds):
            c = Community.get_community(u'mycommunity')
            siteadmin = User.get_user(u'siteadmin')
            siteadmin.record_dynamic_membership(c)

        self.testapp.get(path % '',
                         status=200,
                         extra_environ=site_admin_env)

        # Test site admin can access site community as a non member
        with mock_dataserver.mock_db_trans(self.ds):
            c = Community.get_community(u'mycommunity')
            siteadmin = User.get_user(u'siteadmin')
            siteadmin.record_no_longer_dynamic_member(c)
            interface.alsoProvides(c, ISiteCommunity)

        self.testapp.get(path % '',
                         status=200,
                         extra_environ=site_admin_env)

        # Test site admin can access site community admin views
        self.testapp.get(path % 'ListAdmins',
                         extra_environ=site_admin_env)

        # test non super user can't access
        self.testapp.put_json(path % 'AddAdmin',
                              {'username': 'sjohnson@nextthought.com'},
                              status=403,
                              extra_environ=basic_env)

        self.testapp.put_json(path % 'RemoveAdmin',
                              {'username': 'sjohnson@nextthought.com'},
                              status=403,
                              extra_environ=basic_env)

        # test super user can add
        self.testapp.put_json(path % 'AddAdmin',
                              {'username': 'sheldon'},
                              status=200)

        res = self.testapp.get(path % 'ListAdmins',
                               status=200)
        assert_that(res.json_body, has_length(1))

        # test added user can add now and read
        self.testapp.put_json(path % 'AddAdmin',
                              {'username': 'sjohnson@nextthought.com'},
                              status=200,
                              extra_environ=basic_env)

        res = self.testapp.get(path % 'ListAdmins',
                               status=200,
                               extra_environ=basic_env)
        assert_that(res.json_body, has_length(2))

        # test basic can remove
        self.testapp.put_json(path % 'RemoveAdmin',
                              {'username': 'sheldon'},
                              status=200,
                              extra_environ=basic_env)

        # basic can no longer access
        res = self.testapp.get(path % 'ListAdmins',
                               status=403,
                               extra_environ=basic_env)

        # Only super left
        res = self.testapp.get(path % 'ListAdmins',
                               status=200)
        assert_that(res.json_body, has_length(1))

    def _get_community_workspace_rels(self, env, is_admin=False):
        """
        Validate workspace community state, returning all, admin, joined
        collection hrefs, respectively.
        """
        # Validate workspace state
        res = self.testapp.get('/dataserver2/service', extra_environ=env)
        res = res.json_body
        try:
            comm_ws = next(x for x in res['Items'] if x['Title'] == 'Communities')
        except StopIteration:
            comm_ws = None
        assert_that(comm_ws, not_none())
        collections = comm_ws.get("Items")
        assert_that(collections, has_length(3))
        colls = [x for x in collections if x.get('Title') == 'AllCommunities']
        all_comm = colls[0]
        if is_admin:
            assert_that(all_comm, has_entry('accepts', contains(Community.mime_type)))
        else:
            assert_that(all_comm, does_not(has_entry('accepts', contains(Community.mime_type))))
        all_href = all_comm.get('href')
        colls = [x for x in collections if x.get('Title') == 'AdministeredCommunities']
        admin_href = colls[0].get('href') if colls else None
        colls = [x for x in collections if x.get('Title') == 'Communities']
        joined_href = colls[0].get('href') if colls else None
        assert_that(all_href, not_none())
        assert_that(admin_href, not_none())
        assert_that(joined_href, not_none())
        return all_href, admin_href, joined_href

    @time_monotonically_increases
    @WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=True)
    def test_communities_workspace(self):
        """
        Validate the community workspace. All communities should be tied and
        exposed by the site they belong to.
        """
        with mock_dataserver.mock_db_trans(self.ds):
            self._create_user(u"locke")
            self._create_user(u"terra")

            # Non site community that does not pollute our alpha work
            comm = Community.create_community(username='non_site_community')
            comm.public = True
            comm.joinable = True

        # Community tied to another site is not visible in our alpha site
        with mock_dataserver.mock_db_trans(self.ds, site_name='mathcounts.nextthought.com'):
            comm = Community.create_community(username='mathcounts_test_community')
            comm.public = True
            comm.joinable = True

        non_site_community_href = '/dataserver2/users/non_site_community'
        mc_site_community_href = '/dataserver2/users/mathcounts_test_community'

        locke_env = self._make_extra_environ(user="locke")
        terra_admin_env = self._make_extra_environ(user="terra")

        all_href, admin_href, joined_href = self._get_community_workspace_rels(locke_env)

        # Validate empty
        for href in (all_href, admin_href, joined_href):
            res = self.testapp.get(href, extra_environ=locke_env)
            res = res.json_body
            assert_that(res.get('Items'), has_length(0))

        public_joinable_comm = u'comm1_ws_test'
        public_unjoinable_comm = u'comm2_ws_test'
        private_unjoinable_comm = u'comm3_ws_test'
        with mock_dataserver.mock_db_trans(self.ds, site_name='alpha.nextthought.com'):
            comm = Community.create_community(username=public_joinable_comm)
            comm.public = True
            comm.joinable = True
            comm = Community.create_community(username=public_unjoinable_comm)
            comm.public = True
            comm.joinable = False
            comm = Community.create_community(username=private_unjoinable_comm)
            comm.public = False
            comm.joinable = False

            site = getSite()
            prm = IPrincipalRoleManager(site)
            prm.assignRoleToPrincipal(ROLE_SITE_ADMIN_NAME, 'terra')

        admin_rels = self._get_community_workspace_rels(terra_admin_env, is_admin=True)
        admin_all_href, admin_admin_href, admin_joined_href = admin_rels

        # Validate with communities
        for href in (admin_href, joined_href):
            res = self.testapp.get(href, extra_environ=locke_env)
            res = res.json_body
            assert_that(res.get('Items'), has_length(0))

        res = self.testapp.get(all_href, extra_environ=locke_env)
        res = res.json_body
        comms = res.get('Items')
        assert_that(comms, has_length(1))
        joinable_comm = comms[0]
        assert_that(joinable_comm, has_entries('Username', public_joinable_comm,
                                               'public', True,
                                               'joinable', True))
        join_href = self.require_link_href_with_rel(joinable_comm, 'join')
        self.testapp.post(join_href, extra_environ=locke_env)

        # We joined; now joined does not show up in available, but in joined
        for href in (admin_href, all_href):
            res = self.testapp.get(href, extra_environ=locke_env)
            res = res.json_body
            assert_that(res.get('Items'), has_length(0))

        res = self.testapp.get(joined_href, extra_environ=locke_env)
        res = res.json_body
        comms = res.get('Items')
        assert_that(comms, has_length(1))
        joined_comm = comms[0]
        assert_that(joined_comm, has_entries('Username', public_joinable_comm,
                                             'public', True,
                                             'joinable', True))
        self.require_link_href_with_rel(joined_comm, 'leave')
        self.forbid_link_with_rel(joined_comm, 'join')

        # Site admin can see all communities
        res = self.testapp.get(admin_joined_href, extra_environ=terra_admin_env)
        res = res.json_body
        assert_that(res.get('Items'), has_length(0))

        res = self.testapp.get(admin_all_href, extra_environ=terra_admin_env)
        res = res.json_body
        comms = res.get('Items')
        assert_that(comms, has_length(1))
        joinable_comm = comms[0]
        assert_that(joinable_comm, has_entries('Username', public_joinable_comm,
                                               'public', True,
                                               'joinable', True))

        res = self.testapp.get(admin_admin_href, extra_environ=terra_admin_env)
        res = res.json_body
        comms = res.get('Items')
        assert_that(comms, has_length(3))
        comm_names = [x.get('Username') for x in comms]
        assert_that(comm_names, contains_inanyorder(public_joinable_comm,
                                                    public_unjoinable_comm,
                                                    private_unjoinable_comm))

        # Validate cross site community access
        for href in (mc_site_community_href,):
            for env in (locke_env, terra_admin_env):
                for post_view_name in ('join', 'leave', 'hide', 'unhide'):
                    self.testapp.post('%s/%s' % (href, post_view_name),
                                      extra_environ=env,
                                      status=404)
                self.testapp.get(href, extra_environ=env, status=404)
                self.testapp.get(href + '/members', extra_environ=env, status=404)


        # Create new Community
        self.testapp.post_json(all_href, {}, extra_environ=locke_env,
                               status=403)
        self.testapp.post_json(all_href, {}, extra_environ=terra_admin_env,
                               status=422)
        new_comm1_alias = "new community one"
        data = {'alias': new_comm1_alias,
                'public': True,
                'joinable': True}
        new_comm1 = self.testapp.post_json(all_href, data, extra_environ=terra_admin_env)
        new_comm1 = new_comm1.json_body
        new_comm1_username = 'new_community_one@alpha.nextthought.com'
        assert_that(new_comm1, has_entries('alias', new_comm1_alias,
                                           'Username', new_comm1_username,
                                           'public', True,
                                           'joinable', True,
                                           'RemoteIsMember', False,
                                           'Creator', 'terra',
                                           'CreatedTime', not_none(),
                                           'Last Modified', not_none()))

        # Now one with a duplicate alias
        new_comm2 = self.testapp.post_json(all_href, data, extra_environ=terra_admin_env)
        new_comm2 = new_comm2.json_body
        new_comm2_username = new_comm2.get('Username')
        assert_that(new_comm2, has_entries('alias', new_comm1_alias,
                                           'Username', is_not('new_community_one@alpha.nextthought.com'),
                                           'public', True,
                                           'joinable', True,
                                           'RemoteIsMember', False,
                                           'Creator', 'terra',
                                           'CreatedTime', not_none(),
                                           'Last Modified', not_none()))

        # Validate creation site
        with mock_dataserver.mock_db_trans(self.ds, site_name='alpha.nextthought.com'):
            for comm in (new_comm1_username, new_comm2_username):
                comm = Community.get_community(comm)
                assert_that(get_entity_creation_sitename(comm),
                            is_('alpha.nextthought.com'))

        # Join new community
        res = self.testapp.get(all_href, extra_environ=locke_env)
        res = res.json_body
        comms = res.get('Items')
        assert_that(comms, has_length(2))
        comm_usernames = [x.get('Username') for x in comms]
        assert_that(comm_usernames, contains_inanyorder(new_comm1_username, new_comm2_username))
        comm_ext = [x for x in comms if x.get('Username') == new_comm1_username]
        comm_ext = comm_ext[0]
        new_comm_join_href = self.require_link_href_with_rel(comm_ext, 'join')
        self.testapp.post(new_comm_join_href, extra_environ=locke_env)

        res = self.testapp.get(joined_href, extra_environ=locke_env)
        res = res.json_body
        comms = res.get('Items')
        assert_that(comms, has_length(2))
        comm_names = [x.get('Username') for x in comms]
        assert_that(comm_names, contains_inanyorder(new_comm1_username,
                                                    public_joinable_comm))

        # Member cannot edit or delete community
        for comm_ext in comms:
            for rel in ('edit', 'delete'):
                self.forbid_link_with_rel(comm_ext, rel)

        # Admin can edit and delete
        res = self.testapp.get('/dataserver2/users/%s' % public_joinable_comm,
                               extra_environ=terra_admin_env)
        res = res.json_body
        edit_href = self.require_link_href_with_rel(res, 'edit')

        # Can edit
        res = self.testapp.put_json(edit_href, {"alias" : u"community renamed汉字"},
                                    extra_environ=terra_admin_env)
        res = res.json_body
        assert_that(res.get('alias'), is_(u"community renamed汉字"))

        delete_href = self.require_link_href_with_rel(res, 'delete')
        self.forbid_link_with_rel(res, 'restore')
        self.testapp.delete(delete_href, extra_environ=terra_admin_env)
        # Can delete again without change
        self.testapp.delete(delete_href, extra_environ=terra_admin_env)

        res = self.testapp.get('/dataserver2/users/%s' % public_joinable_comm,
                               extra_environ=terra_admin_env)
        res = res.json_body
        self.forbid_link_with_rel(res, 'delete')
        restore_href = self.require_link_href_with_rel(res, 'restore')

        # Deleted no longer shows up in joined for member
        res = self.testapp.get(joined_href, extra_environ=locke_env)
        res = res.json_body
        comms = res.get('Items')
        assert_that(comms, has_length(1))
        comm = comms[0]
        assert_that(comm, has_entry('Username', new_comm1_username))

        # ...or in available to join
        res = self.testapp.get(all_href, extra_environ=locke_env)
        res = res.json_body
        comms = res.get('Items')
        assert_that(comms, has_length(1))
        comm = comms[0]
        assert_that(comm, has_entry('Username', new_comm2_username))

        # Admin no longer sees it
        res = self.testapp.get(admin_admin_href, extra_environ=terra_admin_env)
        res = res.json_body
        comms = res.get('Items')
        assert_that(comms, has_length(4))
        comm_names = [x.get('Username') for x in comms]
        assert_that(comm_names, contains_inanyorder(public_unjoinable_comm,
                                                    new_comm1_username,
                                                    new_comm2_username,
                                                    private_unjoinable_comm))

        # Validate a user's dynamic memberships
        with mock_dataserver.mock_db_trans(self.ds, site_name='alpha.nextthought.com'):
            user = User.get_user('locke')
            deactivated_community = Community.get_community(public_joinable_comm)
            assert_that(deactivated_community in user.following, is_(False))
            assert_that(user.is_dynamic_member_of(deactivated_community), is_(False))

        # Restore
        self.testapp.post(restore_href, extra_environ=terra_admin_env)

        # Still no longer shows up in joined for member
        res = self.testapp.get(joined_href, extra_environ=locke_env)
        res = res.json_body
        comms = res.get('Items')
        assert_that(comms, has_length(1))
        comm = comms[0]
        assert_that(comm, has_entry('Username', new_comm1_username))

        # ...but does show up in available to join again
        res = self.testapp.get(all_href, extra_environ=locke_env)
        res = res.json_body
        comms = res.get('Items')
        assert_that(comms, has_length(2))
        comm_usernames = [x.get('Username') for x in comms]
        assert_that(comm_usernames, contains_inanyorder(public_joinable_comm,
                                                        new_comm2_username))

        # Admin sees it
        res = self.testapp.get(admin_admin_href, extra_environ=terra_admin_env)
        res = res.json_body
        comms = res.get('Items')
        assert_that(comms, has_length(5))
        comm_names = [x.get('Username') for x in comms]
        assert_that(comm_names, contains_inanyorder(public_joinable_comm,
                                                    public_unjoinable_comm,
                                                    new_comm1_username,
                                                    new_comm2_username,
                                                    private_unjoinable_comm))


    @WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=True)
    def test_community_images(self):
        """
        Validate community image management.
        """
        gif_image_data = 'data:image/gif;base64,R0lGODlhCwALAIAAAAAA3pn/ZiH5BAEAAAEALAAAAAALAAsAAAIUhA+hkcuO4lmNVindo7qyrIXiGBYAOw=='
        png_image_data = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAACXBIWXMAAAsTAAALEwEAmpwYAAACbmlUWHRYTUw6Y29tLmFkb2JlLnhtcAAAAAAAPHg6eG1wbWV0YSB4bWxuczp4PSJhZG9iZTpuczptZXRhLyIgeDp4bXB0az0iWE1QIENvcmUgNS4xLjIiPgogICA8cmRmOlJERiB4bWxuczpyZGY9Imh0dHA6Ly93d3cudzMub3JnLzE5OTkvMDIvMjItcmRmLXN5bnRheC1ucyMiPgogICAgICA8cmRmOkRlc2NyaXB0aW9uIHJkZjphYm91dD0iIgogICAgICAgICAgICB4bWxuczp4bXA9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC8iPgogICAgICAgICA8eG1wOkNyZWF0b3JUb29sPkFjb3JuIHZlcnNpb24gMi42LjU8L3htcDpDcmVhdG9yVG9vbD4KICAgICAgPC9yZGY6RGVzY3JpcHRpb24+CiAgICAgIDxyZGY6RGVzY3JpcHRpb24gcmRmOmFib3V0PSIiCiAgICAgICAgICAgIHhtbG5zOnRpZmY9Imh0dHA6Ly9ucy5hZG9iZS5jb20vdGlmZi8xLjAvIj4KICAgICAgICAgPHRpZmY6Q29tcHJlc3Npb24+NTwvdGlmZjpDb21wcmVzc2lvbj4KICAgICAgICAgPHRpZmY6WVJlc29sdXRpb24+NzI8L3RpZmY6WVJlc29sdXRpb24+CiAgICAgICAgIDx0aWZmOlhSZXNvbHV0aW9uPjcyPC90aWZmOlhSZXNvbHV0aW9uPgogICAgICA8L3JkZjpEZXNjcmlwdGlvbj4KICAgPC9yZGY6UkRGPgo8L3g6eG1wbWV0YT4KO/MupgAAAA1JREFUCB1j+P//PwMACPwC/uYM/6sAAAAASUVORK5CYII='

        with mock_dataserver.mock_db_trans(self.ds):
            comm = Community.create_community(username='community_image_test')
            comm.public = True
            comm.joinable = True

        comm_href = '/dataserver2/users/community_image_test'
        res = self.testapp.get(comm_href)
        res = res.json_body
        assert_that(res, has_entries('avatarURL', not_none(),
                                     'backgroundURL', none(),
                                     'blurredAvatarURL', none()))

        res = self.testapp.put_json(comm_href, {'avatarURL': png_image_data})
        res = res.json_body
        avatar_url = res.get('avatarURL')
        assert_that(avatar_url, not_none())
        self.testapp.get(avatar_url)
        blurred_url = res.get('blurredAvatarURL')
        assert_that(blurred_url, not_none())
        self.testapp.get(blurred_url)

        # Cannot blur GIF so blurred URL is empty again
        res = self.testapp.put_json(comm_href, {'avatarURL': gif_image_data})
        res = res.json_body
        assert_that(res, has_entries('avatarURL', not_none(),
                                     'backgroundURL', none(),
                                     'blurredAvatarURL', none()))
