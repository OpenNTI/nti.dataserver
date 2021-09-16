#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods,arguments-differ

from hamcrest import is_
from hamcrest import none
from hamcrest import is_in
from hamcrest import is_not
from hamcrest import contains
from hamcrest import not_none
from hamcrest import has_item
from hamcrest import has_items
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_entries
from hamcrest import has_property
from hamcrest import contains_string
from hamcrest import contains_inanyorder
does_not = is_not

from nti.testing.matchers import validly_provides

import fudge

from quopri import decodestring

from zope import annotation
from zope import interface
from zope import component
from zope import lifecycleevent

from zope.component import getGlobalSiteManager

from zope.component.hooks import getSite

from zope.interface.interfaces import IComponents

from zope.intid.interfaces import IIntIds

from zope.schema import TextLine

from zope.schema.fieldproperty import createFieldProperties

from zope.securitypolicy.interfaces import IPrincipalRoleManager

from nti.app.users import VIEW_USER_UPSERT
from nti.app.users import VIEW_GRANT_USER_ACCESS
from nti.app.users import VIEW_RESTRICT_USER_ACCESS
from nti.app.users import VIEW_LINK_EXTERNAL_IDS_CSV

from nti.app.users.utils import set_user_creation_site
from nti.app.users.utils import get_user_creation_sitename
from nti.app.users.utils import get_entity_creation_sitename
from nti.app.users.utils import get_verification_signature_data

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.appserver.account_recovery_views import REL_ADMIN_TRIGGERED_PASSCODE_RESET

from nti.appserver.policies.interfaces import ISitePolicyUserEventListener,\
    IRequireSetPassword

from nti.appserver.policies.site_policies import AdultCommunitySitePolicyEventListener

from nti.appserver.tests import ITestMailDelivery

from nti.dataserver.authorization import ROLE_SITE_ADMIN

from nti.dataserver.contenttypes.note import Note

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import ISiteCommunity
from nti.dataserver.interfaces import IAccessProvider

from nti.dataserver.tests import mock_dataserver

from nti.dataserver.users.communities import Community

from nti.dataserver.users.friends_lists import DynamicFriendsList

from nti.dataserver.users.index import get_entity_catalog

from nti.dataserver.users.interfaces import ICompleteUserProfile
from nti.dataserver.users.interfaces import IUserProfile
from nti.dataserver.users.interfaces import IDisallowMembershipOperations

from nti.dataserver.users.user_profile import CompleteUserProfile
from nti.dataserver.users.user_profile import COMPLETE_USER_PROFILE_KEY

from nti.dataserver.users.users import User

from nti.dataserver.users.utils import is_email_verified

from nti.externalization.interfaces import StandardExternalFields

from nti.identifiers.interfaces import IUserExternalIdentityContainer

from nti.identifiers.utils import get_user_for_external_id

from nti.ntiids.oids import to_external_ntiid_oid

from nti.site.hostpolicy import get_all_host_sites

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


class IFakeUserProfile(ICompleteUserProfile):
    test_field = TextLine(title=u'A test field to check different profiles')


@interface.implementer(IFakeUserProfile)
class FakeUserProfile(CompleteUserProfile):
    createFieldProperties(IFakeUserProfile)


FakeUserProfileFactory = annotation.factory(FakeUserProfile,
                                            COMPLETE_USER_PROFILE_KEY)


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
                        has_property('email_verified', is_(None)))
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

        assert_that(res.json_body, has_entry('Signature', has_length(180)))
        assert_that(res.json_body, has_entry('Token', is_(int)))

        sig = res.json_body['Signature']
        with mock_dataserver.mock_db_trans(self.ds):
            user = User.get_user(username)
            data = get_verification_signature_data(user, sig)
            assert_that(data, has_entry('username', is_(u'user_one')))
            assert_that(data, has_entry('email', is_(u'user.one@foo.com')))

    @WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=True)
    def test_set_user_creation_site(self):
        username = u'ichigo'
        with mock_dataserver.mock_db_trans(self.ds):
            User.create_user(username=username)
            sites = list(get_all_host_sites())
            sitename = sites[0].__name__ if sites else 'dataserver2'

        self.testapp.post_json('/dataserver2/@@SetUserCreationSite',
                               {'username': username, 'site': 'invalid_site'},
                               status=422)

        self.testapp.post_json('/dataserver2/@@SetUserCreationSite',
                               {'username': username, 'site': sitename},
                               status=204)

        with mock_dataserver.mock_db_trans(self.ds):
            creation_site = get_user_creation_sitename(username)
            if sitename != 'dataserver2':
                assert_that(creation_site, is_(sitename))

        gsm = getGlobalSiteManager()

        class TestPolicy(AdultCommunitySitePolicyEventListener):
            COM_USERNAME = u'site_community_1'

        try:
            with mock_dataserver.mock_db_trans(self.ds):
                c1 = Community.create_community(username=u'site_community_1')
                c2 = Community.create_community(username=u'site_community_2')
                # To keep our dependencies clean, we explicitly set this
                # rather than import SiteCommunity from nti.app.site
                ISiteCommunity.providedBy(c1)
                ISiteCommunity.providedBy(c2)
                user = User.get_user(username)
                user.record_dynamic_membership(c2)

            gsm.registerUtility(TestPolicy, ISitePolicyUserEventListener)

            # Test users are added to site community and not removed from others
            self.testapp.post_json('/dataserver2/@@SetUserCreationSite?update_site_community=True',
                                   {'username': 'ichigo'},
                                   status=204)
            with mock_dataserver.mock_db_trans(self.ds):
                user = User.get_user(username)
                assert_that(user, is_in(c1))
                assert_that(user, is_in(c2))

            # Test users are added to site community and removed from others
            self.testapp.post_json('/dataserver2/@@SetUserCreationSite?update_site_community=True&remove_all_others=True',
                                   {'username': 'ichigo'},
                                   status=204)
            with mock_dataserver.mock_db_trans(self.ds):
                user = User.get_user(username)
                assert_that(user, is_in(c1))
                assert_that(user, not is_in(c2))

        finally:
            gsm.unregisterUtility(TestPolicy, ISitePolicyUserEventListener)

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

        with mock_dataserver.mock_db_trans(self.ds):
            User.create_user(username='user_two')

        self.testapp.delete('/dataserver2/users/%s' % self.default_username,
                            status=422)

        self.testapp.delete('/dataserver2/users/user_two',
                            status=204)

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

    def _get_workspace(self, name, env=None):
        service_doc = '/dataserver2/service'
        res = self.testapp.get(service_doc, extra_environ=env)
        res = res.json_body
        result = next(x for x in res[ITEMS] if x['Title'] == name)
        return result

    @WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=True)
    def test_user_update(self):
        # Default environ with alpha
        self.testapp.extra_environ['HTTP_ORIGIN'] = 'http://alpha.nextthought.com'
        global_workspace = self._get_workspace(u'Global')
        catalog_workspace = self._get_workspace(u'Catalog')
        user_workspace = self._get_workspace(self.default_username.lower())
        username = u'ed_brubaker'
        username2 = u'ed_brubaker_duplicate'
        external_type = u'employee id'
        external_id = u'1112345'
        with mock_dataserver.mock_db_trans(self.ds):
            user = self._create_user(username)
            user2 = self._create_user(username2)
            catalog = get_entity_catalog()
            intids = component.getUtility(IIntIds)
            doc_id = intids.getId(user)
            catalog.index_doc(doc_id, user)
            user_ntiid = to_external_ntiid_oid(user)
            invalid_access_ntiid = to_external_ntiid_oid(user.__parent__)
            set_user_creation_site(user, 'alpha.nextthought.com')
            set_user_creation_site(user2, 'alpha.nextthought.com')

        # Resolve user can get via external identity
        self.testapp.get('/dataserver2/ResolveUser', status=404)
        resolve_url = '/dataserver2/ResolveUser?external_type=%s&external_id=%s' % (external_type, external_id)
        resolve_res = self.testapp.get(resolve_url).json_body
        resolve_res = resolve_res['Items']
        assert_that(resolve_res, has_length(0))
        # Set external ids via admin view
        admin_external_href = '/dataserver2/users/%s/%s' % (username, 'LinkUserExternalIdentity')
        self.testapp.post_json(admin_external_href, {'external_type': external_type,
                                                     'external_id': external_id})
        # Cannot map to different user
        admin_external_href = '/dataserver2/users/%s/%s' % (username2, 'LinkUserExternalIdentity')
        self.testapp.post_json(admin_external_href, {'external_type': external_type,
                                                     'external_id': external_id},
                               status=422)

        resolve_res = self.testapp.get(resolve_url).json_body
        resolve_res = resolve_res['Items']
        assert_that(resolve_res, has_length(1))
        resolve_res = resolve_res[0]
        assert_that(resolve_res, has_entries('external_ids',
                                             has_entries(external_type, external_id),
                                             'Username', username))

        # Can in a different site though
        environ = self._make_extra_environ()
        environ['HTTP_ORIGIN'] = 'http://mathcounts.nextthought.com'
        admin_external_href = '/dataserver2/users/%s/%s' % (username2, 'LinkUserExternalIdentity')
        self.testapp.post_json(admin_external_href, {'external_type': external_type,
                                                     'external_id': external_id},
                               extra_environ=environ)

        user1_environ = self._make_extra_environ(user=username)
        user1_environ['HTTP_ORIGIN'] = 'http://alpha.nextthought.com'

        user_update_href = self.require_link_href_with_rel(global_workspace,
                                                           VIEW_USER_UPSERT)

        grant_access_href = self.require_link_href_with_rel(catalog_workspace,
                                                            VIEW_GRANT_USER_ACCESS)

        remove_access_href = self.require_link_href_with_rel(catalog_workspace,
                                                             VIEW_RESTRICT_USER_ACCESS)

        link_external_ids_csv_href = self.require_link_href_with_rel(user_workspace,
                                                                     VIEW_LINK_EXTERNAL_IDS_CSV)

        # Empty update succeeds
        user_update_href_username = '%s?username=%s' % (user_update_href, username)
        self.testapp.post_json(user_update_href_username)

        # Update user
        new_first = u'Ed'
        new_last = u'Brubaker'
        new_email = u'new_email@gmail.com'
        data1 = {u'first_name': new_first,
                 u'last_name': new_last,
                 u'external_type': external_type,
                 u'external_id': external_id,
                 u'email': new_email}
        self.testapp.post_json(user_update_href, data1)
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
        data2 = {u'first_name': new_first,
                  u'last_name': new_last,
                  u'external_type': new_external_type,
                  u'external_id': new_external_id,
                  u'email': new_email}
        res = self.testapp.post_json(user_update_href, data2)
        res = res.json_body
        created_username = res.get('Username')
        assert_that(created_username, is_not(new_email))

        with mock_dataserver.mock_db_trans(self.ds):
            user = User.get_user(created_username)
            user.password = 'temp001'
        user2_environ = self._make_extra_environ(user=created_username)
        user2_environ['HTTP_ORIGIN'] = 'http://alpha.nextthought.com'

        res = self.testapp.get('/dataserver2/users/%s' % created_username,
                               extra_environ=user2_environ)
        res = res.json_body
        assert_that(res['realname'], is_('%s %s' % (new_first, new_last)))
        assert_that(res['email'], is_(new_email))

        # Batch user upserts
        batch_data1 = dict(data1)
        batch_data2 = dict(data2)
        batch_data2['real_name'] = "user2 madeupname"
        bad_data = {'username': 'newusername3',
                     'external_type': external_type,
                     'external_id': '78787878',
                     'realname': "invalidrealname",
                     'email': "dupeuser@gmail.com"}
        batch_data = [batch_data1, batch_data2, bad_data]

        # First batch has invalid username
        res = self.testapp.post_json(user_update_href, batch_data, status=422)
        res = res.json_body
        messages = [x.get('message') for x in res]
        assert_that(messages, has_length(3))
        assert_that(messages, contains(u'Success',
                                       u'Success',
                                       u'Please provide your first and last names.'))

        # Valid user2 info is unchanged
        res = self.testapp.get('/dataserver2/users/%s' % created_username,
                               extra_environ=user2_environ)
        res = res.json_body
        assert_that(res['realname'], is_('%s %s' % (new_first, new_last)))
        assert_that(res['email'], is_(new_email))

        # Multiple errors
        bad_data['realname'] = 'newuser goodname'
        bad_data['email'] = 'invalidemail'
        batch_data2['external_type'] = None
        batch_data1['external_id'] = None
        res = self.testapp.post_json(user_update_href, batch_data, status=422)
        res = res.json_body
        messages = [x.get('message') for x in res]
        assert_that(messages, has_length(3))
        assert_that(messages, contains(u'Must provide external_type and external_id.',
                                       u'Must provide external_type and external_id.',
                                       u'The email address you have entered is not valid.'))

        # Successful update
        good_data = bad_data
        good_data['require_password'] = True
        good_data['email'] = 'validemail@gmail.com'
        batch_data1 = dict(data1)
        batch_data2 = dict(data2)
        batch_data1['real_name'] = "Naomi Ngata"
        batch_data1['update'] = False
        batch_data2['real_name'] = "user2 madeupname"
        batch_data = [batch_data1, good_data, batch_data2]

        res = self.testapp.post_json(user_update_href, batch_data)
        res = res.json_body
        messages = [x.get('message') for x in res]
        assert_that(messages, has_length(3))
        assert_that(messages, contains(u'Success',
                                       u'Success',
                                       u'Success'))

        # User1 *is not* updated since we asked it not to
        res = self.testapp.get('/dataserver2/users/%s' % username,
                               extra_environ=user1_environ)
        res = res.json_body
        assert_that(res['realname'], is_(u'Ed Brubaker'))
        assert_that(res['email'], is_(u'new_email@gmail.com'))

        # User2 was properly updated
        res = self.testapp.get('/dataserver2/users/%s' % created_username,
                               extra_environ=user2_environ)
        res = res.json_body
        assert_that(res['realname'], is_("user2 madeupname"))
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

        # Batch grant/remove
        res = self.testapp.post_json(grant_access_href,
                               [full_data, invalid_access], status=422)
        res = res.json_body
        messages = [x.get('message') for x in res]
        assert_that(messages, has_length(2))
        assert_that(messages, contains(u'Success',
                                       u'Cannot grant access to object.'))
        res = self.testapp.post_json(grant_access_href,
                               [full_data, invalid_access, missing_user2, missing_user],
                               status=422)
        res = res.json_body
        messages = [x.get('message') for x in res]
        assert_that(messages, has_length(4))
        assert_that(messages, contains(u'Success',
                                       u'Cannot grant access to object.',
                                       u'User not found.',
                                       u'User not found.'))
        res = self.testapp.post_json(grant_access_href,
                               [full_data, full_data, full_data, full_data])
        res = res.json_body
        messages = [x.get('message') for x in res]
        assert_that(messages, has_length(4))
        assert_that(messages, contains(u'Success',
                                       u'Success',
                                       u'Success',
                                       u'Success'))

        # Resolving user
        resolve_href = '/dataserver2/ResolveUser/%s' % created_username
        resolve_res = self.testapp.get(resolve_href)
        resolve_res = resolve_res.json_body
        resolve_res = resolve_res['Items']
        assert_that(resolve_res, has_length(1))
        resolve_res = resolve_res[0]
        assert_that(resolve_res, has_entry('external_ids',
                                           has_entries(new_external_type, new_external_id)))

        # Different site for username returns correct site external identifiers
        resolve_href = '/dataserver2/ResolveUser/%s?filter_by_site_community=False' % created_username
        resolve_res = self.testapp.get(resolve_href, extra_environ=environ)
        resolve_res = resolve_res.json_body
        resolve_res = resolve_res['Items']
        assert_that(resolve_res, has_length(1))
        resolve_res = resolve_res[0]
        assert_that(resolve_res, does_not(has_item('external_ids')))

        resolve_href = '/dataserver2/ResolveUser/%s' % username
        resolve_res = self.testapp.get(resolve_href)
        resolve_res = resolve_res.json_body
        resolve_res = resolve_res['Items']
        assert_that(resolve_res, has_length(1))
        resolve_res = resolve_res[0]
        assert_that(resolve_res, has_entry('external_ids',
                                           has_entries(external_type, external_id)))

        resolve_href = '/dataserver2/ResolveUser/%s' % username2
        resolve_res = self.testapp.get(resolve_href)
        resolve_res = resolve_res.json_body
        resolve_res = resolve_res['Items']
        assert_that(resolve_res, has_length(1))
        resolve_res = resolve_res[0]
        assert_that(resolve_res, does_not(has_item('external_ids')))

        # Test custom profile updates

        # We don't want to do this in a DB transaction as this is a non-persistent registration
        # Instead, we will directly query for the non-persistent registry
        alpha = component.getUtility(IComponents, name='alpha.nextthought.com')
        alpha.registerAdapter(FakeUserProfileFactory,
                              provided=IFakeUserProfile,
                              required=(IUser,))
        alpha_environ = self._make_extra_environ()
        alpha_environ['HTTP_ORIGIN'] = 'http://alpha.nextthought.com'
        new_first = u'Alpha'
        new_last = u'User'
        new_email = u'alpha@gmail.com'
        new_external_id = '88888'
        new_external_type = 'employee id'
        self.testapp.post_json(user_update_href,
                              {u'first_name': new_first,
                               u'last_name': new_last,
                               u'external_type': new_external_type,
                               u'external_id': new_external_id,
                               u'email': new_email,
                               u'test_field': u'This is a test field.'},
                               extra_environ=alpha_environ)
        with mock_dataserver.mock_db_trans(self.ds, site_name='alpha.nextthought.com'):
            user = get_user_for_external_id(new_external_type, new_external_id)
            created_username2 = user.username
            profile = ICompleteUserProfile(user)
            assert_that(profile, validly_provides(IFakeUserProfile))
            # Must reset this to alpha or we'll err.
            user2 = User.get_user(username2)
            container = IUserExternalIdentityContainer(user2)
            container.site_name = u'alpha.nextthought.com'

        # Profile in mathcounts env is unaffected
        new_first = u'Default'
        new_last = u'User'
        new_email = u'default@gmail.com'
        new_external_id = '77777'
        new_external_type = 'employee id'
        self.testapp.post_json(user_update_href,
                              {u'first_name': new_first,
                               u'last_name': new_last,
                               u'external_type': new_external_type,
                               u'external_id': new_external_id,
                               u'email': new_email,
                               u'test_field': u'This is a test field.'},
                               extra_environ=environ)

        # CSV link of external ids
        # Invalid headers
        bad_source1 = [u'bad_id,external_type,external_id',]
        bad_source2 = [u'email,missing_external_type,external_id',]
        bad_source3 = [u'usernames,external_type,missing_external_id',]
        for source in (bad_source1, bad_source2, bad_source3):
            base_source_str = str(u'\n'.join(source))
            self.testapp.post(link_external_ids_csv_href,
                              upload_files=[('csv', 'link_external_ids.csv', base_source_str)],
                              status=422)

        # Current state
#         username = u'ed_brubaker'
#         external_type = u'employee id'
#         external_id = u'1112345'
#         new_email = u'new_email@gmail.com'
#
#         new_email = u'parish@gmail.com'
#         created_username
#         new_external_id = '99999'
#         new_external_type = 'employee id'
#
#         new_email = u'alpha@gmail.com'
#         created_username2
#         new_external_id = '88888'
#         new_external_type = 'employee id'
#
#         # MC users
#         username2 = u'ed_brubaker_duplicate'
#         external_type = u'employee id'
#         external_id = u'1112345'
#         new_email = u'default@gmail.com'
#         new_external_id = '77777'
#         new_external_type = 'employee id'

        # Can change a single users mapping further down
        # Can re-use another users ids later in file too
        # Can match ids of user in another site (new_external_type/new_external_id)
        usernames_source = [u'username,external_type,external_id',
                            '%s,%s,%s' % (username, external_type, external_id),
                            '%s,%s,%s' % (username, external_type, ' new id 1'),
                            '%s,%s,%s' % ('usernamenotfound', external_type, ' new id 1'),
                            '%s,%s,%s' % (username2, external_type, ' new id 1'),
                            '%s,%s,%s' % (username2, external_type, external_id),
                            '%s,%s,%s' % (created_username, new_external_type, new_external_id)]
        # u'default@gmail.com' will not be found (mathcounts)
        emails_source = [u'email,external_type,external_id',
                         u'missing_email@gmail.com,%s,%s' % (external_type, external_id),
                         u'parish@gmail.com,%s,%s' % (external_type, ' new id 1'),
                         u'default@gmail.com,%s,%s' % (external_type, ' new id 1'),
                         u'alpha@gmail.com,%s,%s' % (external_type, ' new id 1'),
                         u'alpha@gmail.com,%s,%s' % (external_type, 'new alpha id'),
                         u'parish@gmail.com,%s,%s' % (new_external_type, new_external_id)]
        usernames_source = str(u'\n'.join(usernames_source))
        emails_source = str(u'\n'.join(emails_source))

        self.testapp.post(link_external_ids_csv_href,
                          upload_files=[('csv', 'link_external_ids.csv', usernames_source)],
                          extra_environ=user2_environ,
                          status=403)
        res = self.testapp.post(link_external_ids_csv_href,
                                upload_files=[('csv', 'link_external_ids.csv', usernames_source)])
        res = res.json_body
        assert_that(res['Issues'], has_items(has_entries('username', 'usernamenotfound',
                                                         'issue', 'Cannot find user'),
                                             has_entries('username', username2,
                                                         'issue', 'User already tied to external id',
                                                         'found_user', username,
                                                         'external_id', 'new id 1',
                                                         'external_type', external_type)))
        assert_that(res['Items'], has_items(has_entries('username', username,
                                                        'external_id', 'new id 1',
                                                        'external_type', external_type),
                                            has_entries('username', created_username,
                                                        'external_id', new_external_id,
                                                        'external_type', new_external_type),
                                            has_entries('username', username2,
                                                        'external_id', external_id,
                                                        'external_type', external_type)))
        # Now CSV link lookup by emails
        # A duplicate email for username
        self.testapp.post_json(user_update_href, {u'external_type': external_type,
                                                  u'external_id': 'new id 1',
                                                  u'email': u'parish@gmail.com'})
        res = self.testapp.post(link_external_ids_csv_href,
                                upload_files=[('csv', 'link_external_ids.csv', emails_source)])
        res = res.json_body
        assert_that(res['Issues'], has_items(has_entries('email', u'missing_email@gmail.com',
                                                         'issue', 'Cannot find user'),
                                             has_entries('email', u'default@gmail.com',
                                                         'issue', 'Cannot find user'),
                                             has_entries('email', 'alpha@gmail.com',
                                                         'issue', u'User already tied to external id',
                                                         u'external_id', u'new id 1',
                                                         u'external_type', u'employee id',
                                                         u'found_user', u'ed_brubaker'),
                                             has_entries('usernames', contains_string('ed_brubaker'),
                                                         'issue', 'Multiple users found for email',
                                                         'email', 'parish@gmail.com')))
        assert_that(res['Items'], has_items(has_entries('username', created_username2,
                                                        'email', u'alpha@gmail.com',
                                                        'external_id', 'new alpha id',
                                                        'external_type', external_type)))

        # Validate external identifiers state
        with mock_dataserver.mock_db_trans(self.ds, site_name='alpha.nextthought.com'):
            user = get_user_for_external_id(new_external_type, 'new alpha id')
            assert_that(user.username, is_(created_username2))
            user = get_user_for_external_id(external_type, 'new id 1')
            assert_that(user.username, is_(username))
            user = get_user_for_external_id(external_type, external_id)
            assert_that(user.username, is_(username2))
            user = get_user_for_external_id(new_external_type, new_external_id)
            assert_that(user.username, is_(created_username))

        with mock_dataserver.mock_db_trans(self.ds, site_name='mathcounts.nextthought.com'):
            user = get_user_for_external_id(new_external_type, new_external_id)
            profile = ICompleteUserProfile(user)
            assert_that(profile, does_not(validly_provides(IFakeUserProfile)))
            assert_that(profile, does_not(has_property('test_field')))

        alpha.unregisterAdapter(FakeUserProfileFactory,
                                provided=IFakeUserProfile,
                                required=(IUser,))

    @WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=True)
    @fudge.patch('nti.app.users.utils.admin.is_site_admin',
                 'nti.app.users.views.view_mixins.is_admin_or_site_admin',
                 'nti.app.users.decorators.is_admin')
    def test_user_update_site_admin(self, mock_site_admin, mock_site_admin2, mock_admin):
        """
        Validate site admins can only update users in their site.
        """
        mock_site_admin.is_callable().returns(True)
        mock_site_admin2.is_callable().returns(True)
        mock_admin.is_callable().returns(True)
        test_site_username = u'test_site_user'
        test_site_admin_username = u'test_site_admin'
        community_name = u'test_site_admin_community'
        test_site_email = u'%s@gmail.com' % test_site_username
        external_type = u'employee id'
        external_id = u'1112345'

        with mock_dataserver.mock_db_trans(self.ds):
            user = self._create_user(test_site_username)
            site_admin = self._create_user(test_site_admin_username)
            IUserProfile(user).email = test_site_email
            catalog = get_entity_catalog()
            intids = component.getUtility(IIntIds)
            doc_id = intids.getId(user)
            catalog.index_doc(doc_id, user)
            community = Community.create_community(username=community_name)
            site_admin.record_dynamic_membership(community)
            set_user_creation_site(user, 'alpha.dev')
            set_user_creation_site(site_admin, 'alpha.dev')

        admin_environ = self._make_extra_environ(user=test_site_admin_username)
        admin_environ['HTTP_ORIGIN'] = 'http://alpha.dev'
        nt_environ = self._make_extra_environ()
        nt_environ['HTTP_ORIGIN'] = 'http://alpha.dev'

        admin_external_href = '/dataserver2/users/%s/%s' % (test_site_username,
                                                            'LinkUserExternalIdentity')
        self.testapp.post_json(admin_external_href, {'external_type': external_type,
                                                     'external_id': external_id},
                               extra_environ=nt_environ)

        global_workspace = self._get_workspace(u'Global')
        user_update_href = self.require_link_href_with_rel(global_workspace,
                                                           VIEW_USER_UPSERT)

        data = {'realname': "John Smith",
                'external_type': external_type,
                'external_id': external_id}
        self.testapp.post_json(user_update_href, data, extra_environ=admin_environ)

        with mock_dataserver.mock_db_trans(self.ds):
            user = User.get_user(test_site_username)
            set_user_creation_site(user, 'non_existent')
        self.testapp.post_json(user_update_href, data, extra_environ=admin_environ, status=403)

        with mock_dataserver.mock_db_trans(self.ds):
            user = User.get_user(test_site_username)
            set_user_creation_site(user, 'fake')
        self.testapp.post_json(user_update_href, data, extra_environ=admin_environ, status=403)

        # Now add user to community and site admin can administer them
        with mock_dataserver.mock_db_trans(self.ds):
            user = User.get_user(test_site_username)
            community = Community.get_community(community_name)
            user.record_dynamic_membership(community)

        self.testapp.post_json(user_update_href, data, extra_environ=admin_environ)
        res = self.testapp.post_json(user_update_href, data, extra_environ=admin_environ)
        self.forbid_link_with_rel(res.json_body, 'AdminUserUpdate')

        with mock_dataserver.mock_db_trans(self.ds):
            user = User.get_user(test_site_username)
            interface.alsoProvides(user, IRequireSetPassword)

        res = self.testapp.post_json(user_update_href, data, extra_environ=admin_environ)
        update_href = self.require_link_href_with_rel(res.json_body, 'AdminUserUpdate')
        res = self.testapp.put_json(update_href,
                                    {'email': 'newemail@gmail.com'})
        assert_that(res.json_body, has_entry('email', 'newemail@gmail.com'))

    @WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=True)
    def test_user_deactivate(self):
        """
        Validate user deactivation
        """
        test_username = u'test_deactivate_user'
        test_other_username = u'test_deactivate_other'
        test_admin_username = u'test_deactivate_admin'
        test_email = u'%s@gmail.com' % test_username

        with mock_dataserver.mock_db_trans(self.ds):
            user = self._create_user(test_username)
            site_admin = self._create_user(test_admin_username)
            other_user = self._create_user(test_other_username)
            IUserProfile(user).email = test_email
            catalog = get_entity_catalog()
            intids = component.getUtility(IIntIds)
            doc_id = intids.getId(user)
            catalog.index_doc(doc_id, user)
            set_user_creation_site(user, 'alpha.dev')
            set_user_creation_site(other_user, 'alpha.dev')
            set_user_creation_site(site_admin, 'alpha.dev')

        with mock_dataserver.mock_db_trans(self.ds, site_name='alpha.dev'):
            principal_role_manager = IPrincipalRoleManager(getSite())
            principal_role_manager.assignRoleToPrincipal(ROLE_SITE_ADMIN.id,
                                                         test_admin_username)

        admin_environ = self._make_extra_environ(user=test_admin_username)
        admin_environ['HTTP_ORIGIN'] = 'http://alpha.dev'
        user_environ = self._make_extra_environ(user=test_username)
        user_environ['HTTP_ORIGIN'] = 'http://alpha.dev'
        other_environ = self._make_extra_environ(user=test_other_username)
        other_environ['HTTP_ORIGIN'] = 'http://alpha.dev'
        nt_admin_environ = self._make_extra_environ()
        nt_admin_environ['HTTP_ORIGIN'] = 'http://alpha.dev'

        user_workspace = self._get_workspace(test_admin_username, admin_environ)
        batch_deactivate_href = self.require_link_href_with_rel(user_workspace,
                                                                'BatchDeactivate')
        batch_reactivate_href = self.require_link_href_with_rel(user_workspace,
                                                                'BatchReactivate')

        resolve_url = '/dataserver2/ResolveUser/%s' % test_username
        def get_user_res():
            res = self.testapp.get(resolve_url, extra_environ=admin_environ)
            res = res.json_body
            return res['Items'][0]
        res = get_user_res()
        deactivate_href = self.require_link_href_with_rel(res, 'Deactivate')
        self.forbid_link_with_rel(res, 'Restore')

        self.testapp.post(deactivate_href, extra_environ=user_environ, status=403)
        self.testapp.post(deactivate_href, extra_environ=other_environ, status=403)
        self.testapp.post(deactivate_href, extra_environ=admin_environ)

        res = get_user_res()
        self.forbid_link_with_rel(res, 'Deactivate')
        assert_that(res, has_entry('Deactivated', True))
        restore_href = self.require_link_href_with_rel(res, 'Restore')

        # User can no longer login
        self.testapp.post(restore_href, extra_environ=user_environ, status=401)
        self.testapp.post(restore_href, extra_environ=other_environ, status=403)
        self.testapp.post(restore_href, extra_environ=admin_environ)

        # Restored, they do authenticate again
        self.testapp.post(restore_href, extra_environ=user_environ, status=403)
        self.testapp.post(restore_href, extra_environ=other_environ, status=403)
        self.testapp.post(restore_href, extra_environ=admin_environ)

        # Batch deactivation
        data = {'usernames': [test_username, test_other_username, 'name_dne']}
        res = self.testapp.post_json(batch_deactivate_href, data,
                                     extra_environ=admin_environ)
        res = res.json_body
        assert_that(res.get('Total'), is_(2))
        assert_that(res.get(ITEMS),
                    contains_inanyorder(has_entry('Username', test_username),
                                        has_entry('Username', test_other_username)))
        assert_that(res.get('MissingUsers'), contains('name_dne'))
        self.testapp.get('/dataserver2/users/%s' % test_username,
                         extra_environ=user_environ, status=401)
        self.testapp.get('/dataserver2/users/%s' % test_other_username,
                         extra_environ=other_environ, status=401)

        headers = {'accept': str('application/json')}
        res = self.testapp.get('/dataserver2/users/SiteUsers?deactivated=True',
                               headers=headers,
                               extra_environ=nt_admin_environ)
        res = res.json_body
        assert_that(res['ItemCount'], is_(2))

        res = self.testapp.get('/dataserver2/users/SiteUsers?deactivated=False',
                               headers=headers,
                               extra_environ=nt_admin_environ)
        res = res.json_body
        assert_that(res['ItemCount'], is_(0))

        res = self.testapp.get('/dataserver2/users/SiteUsers',
                               headers=headers,
                               extra_environ=nt_admin_environ)
        res = res.json_body
        assert_that(res['ItemCount'], is_(2))

        # Batch reactivation
        data = {'usernames': [test_username, 'name_dne']}
        res = self.testapp.post_json(batch_reactivate_href, data,
                                     extra_environ=admin_environ)
        res = res.json_body
        assert_that(res.get('Total'), is_(1))
        assert_that(res.get(ITEMS), contains(has_entry('Username', test_username)))
        assert_that(res.get('MissingUsers'), contains('name_dne'))
        self.testapp.get('/dataserver2/users/%s' % test_username,
                         extra_environ=user_environ)
        self.testapp.get('/dataserver2/users/%s' % test_other_username,
                         extra_environ=other_environ, status=401)

        res = self.testapp.get('/dataserver2/users/SiteUsers?deactivated=True',
                               headers=headers,
                               extra_environ=nt_admin_environ)
        res = res.json_body
        assert_that(res['ItemCount'], is_(1))

        res = self.testapp.get('/dataserver2/users/SiteUsers?deactivated=False',
                               headers=headers,
                               extra_environ=nt_admin_environ)
        res = res.json_body
        assert_that(res['ItemCount'], is_(1))

        res = self.testapp.get('/dataserver2/users/SiteUsers',
                               headers=headers,
                               extra_environ=nt_admin_environ)
        res = res.json_body
        assert_that(res['ItemCount'], is_(2))
        
    @WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=True)
    def test_admin_triggered_passcode_reset(self):
        """
        Validate admins can trigger a password reset for a user, and only users they have permission over
        """
        test_username = u'test_user_passcode_reset'
        test_admin_username = u'test_reset_admin'
        test_email = u'%s@gmail.com' % test_username
    
        with mock_dataserver.mock_db_trans(self.ds):
            user = self._create_user(test_username)
            site_admin = self._create_user(test_admin_username)
            IUserProfile(user).email = test_email
            IUserProfile(site_admin).alias = u'Test Admin'
            catalog = get_entity_catalog()
            intids = component.getUtility(IIntIds)
            doc_id = intids.getId(user)
            catalog.index_doc(doc_id, user)
            set_user_creation_site(user, 'alpha.dev')
            set_user_creation_site(site_admin, 'alpha.dev')
    
        with mock_dataserver.mock_db_trans(self.ds, site_name='alpha.dev'):
            principal_role_manager = IPrincipalRoleManager(getSite())
            principal_role_manager.assignRoleToPrincipal(ROLE_SITE_ADMIN.id,
                                                         test_admin_username)
    
        admin_environ = self._make_extra_environ(user=test_admin_username)
        admin_environ['HTTP_ORIGIN'] = 'http://alpha.dev'
        user_environ = self._make_extra_environ(user=test_username)
        user_environ['HTTP_ORIGIN'] = 'http://alpha.dev'
        nt_admin_environ = self._make_extra_environ()
        nt_admin_environ['HTTP_ORIGIN'] = 'http://alpha.dev'
    
        resolve_url = '/dataserver2/ResolveUser/%s' % test_username
        res = self.testapp.get(resolve_url, extra_environ=admin_environ)
        res = res.json_body
        res = res['Items'][0]
        
        mailer = component.getUtility( ITestMailDelivery )
    
        admin_triggered_user_passcode_reset_href = self.require_link_href_with_rel(res, REL_ADMIN_TRIGGERED_PASSCODE_RESET)
        data = {'success': 'http://localhost/place'}
        self.testapp.post(admin_triggered_user_passcode_reset_href, data, content_type='application/x-www-form-urlencoded', 
                          extra_environ=admin_environ, status=204)
        self.testapp.post(admin_triggered_user_passcode_reset_href, data, content_type='application/x-www-form-urlencoded', 
                          extra_environ=nt_admin_environ, status=204)
        self.testapp.post(admin_triggered_user_passcode_reset_href, data, content_type='application/x-www-form-urlencoded', 
                          extra_environ=user_environ, status=403)
        assert_that( mailer.queue, has_length( 2 ) )

        with mock_dataserver.mock_db_trans(self.ds):
            user = User.get_user(test_username)
            set_user_creation_site(user, 'fake')
        self.testapp.post(admin_triggered_user_passcode_reset_href, data, content_type='application/x-www-form-urlencoded', 
                          extra_environ=admin_environ, status=403)
        self.testapp.post(admin_triggered_user_passcode_reset_href, data, content_type='application/x-www-form-urlencoded', 
                          extra_environ=nt_admin_environ, status=204)
        assert_that( mailer.queue, has_length( 3 ) )
        
        subject = mailer.queue[0].subject
        assert_that(subject, contains_string('NextThought Password Reset'))
        
        msg = mailer.queue[0]
        assert_that(decodestring(msg.body), contains_string('Test Admin'))
        
        msg = mailer.queue[1]
        assert_that(decodestring(msg.body), contains_string('an Administrator'))

    @WithSharedApplicationMockDS(users=(u'test001', u'test002', u'admin001@nextthought.com'), testapp=True,
                                 default_authenticate=True)
    def test_communities(self):
        path = '/dataserver2/users/test001/@@communities'
        res = self.testapp.get(path,
                               extra_environ=self._make_extra_environ(user=u"admin001@nextthought.com"),
                               status=200)
        assert_that([x['ID'] for x in res.json_body['Items']], contains_inanyorder('Everyone'))

        with mock_dataserver.mock_db_trans(self.ds):
            c1 = Community.create_community(username=u'bleach')
            c2 = Community.create_community(username=u'operation_disallowed')

            for username in (u'test001', u'test002'):
                user = User.get_user(username)
                for c in (c1, c2):
                    user.record_dynamic_membership(c)

            interface.alsoProvides(c2, IDisallowMembershipOperations)

        self.testapp.get(path,
                         extra_environ=self._make_extra_environ(user=u"test002"),
                         status=403)

        res = self.testapp.get(path,
                               extra_environ=self._make_extra_environ(user=u"test001"),
                               status=200)

        assert_that([x['ID'] for x in res.json_body['Items']],
                    contains_inanyorder(u'Everyone', u'bleach', u'operation_disallowed'))

        res = self.testapp.get(path,
                               extra_environ=self._make_extra_environ(user=u"admin001@nextthought.com"),
                               status=200)

        assert_that([x['ID'] for x in res.json_body['Items']],
                    contains_inanyorder(u'Everyone', u'bleach', u'operation_disallowed'))

        # test002
        path = '/dataserver2/users/test002/@@communities'
        res = self.testapp.get(path,
                               extra_environ=self._make_extra_environ(user=u"test002"),
                               status=200)

        assert_that([x['ID'] for x in res.json_body['Items']],
                    contains_inanyorder(u'Everyone', u'bleach', u'operation_disallowed'))

        path = '/dataserver2/users/test002/@@communities?searchTerm=blea'
        res = self.testapp.get(path,
                               extra_environ=self._make_extra_environ(user=u"test002"),
                               status=200)
        assert_that(res.json_body, has_entry('Items', has_length(1)))

    @WithSharedApplicationMockDS(users=(u'test001', u'test002', u'admin001@nextthought.com'), testapp=True,
                                 default_authenticate=True)
    def test_drop_user_from_community(self):

        with mock_dataserver.mock_db_trans(self.ds):
            c1 = Community.create_community(username=u'site_community_1')
            # To keep our dependencies clean, we explicitly set this rather than import SiteCommunity from nti.app.site
            ISiteCommunity.providedBy(c1)
            for username in (u'test001', u'test002'):
                user = User.get_user(username)
                user.record_dynamic_membership(c1)

        # Test users are removed from community
        self.testapp.delete_json('/dataserver2/users/site_community_1/@@admin_drop',
                                 {'usernames': 'test001,test002'},
                                 extra_environ=self._make_extra_environ(user=u'admin001@nextthought.com'),
                                 status=200)
        with mock_dataserver.mock_db_trans(self.ds):
            for username in (u'test001', u'test002'):
                user = User.get_user(username)
                assert_that(user, not is_in(c1))

    @WithSharedApplicationMockDS(users=(u'test001', u'test002', u'admin001@nextthought.com'), testapp=True,
                                 default_authenticate=True)
    def test_add_user_to_community(self):

        with mock_dataserver.mock_db_trans(self.ds):
            c1 = Community.create_community(username=u'site_community_1')
            # To keep our dependencies clean, we explicitly set this rather than import SiteCommunity from nti.app.site
            ISiteCommunity.providedBy(c1)

        # Test users are removed from community
        self.testapp.post_json('/dataserver2/users/site_community_1/@@admin_add',
                               {'usernames': 'test001,test002'},
                               extra_environ=self._make_extra_environ(user=u'admin001@nextthought.com'),
                               status=200)

        with mock_dataserver.mock_db_trans(self.ds):
            for username in (u'test001', u'test002'):
                user = User.get_user(username)
                assert_that(user, is_in(c1))

    @WithSharedApplicationMockDS(users=(u'test001', u'test002', u'admin001@nextthought.com'), testapp=True,
                                 default_authenticate=True)
    def test_reset_site_community(self):
        gsm = getGlobalSiteManager()

        class TestPolicy(AdultCommunitySitePolicyEventListener):
            COM_USERNAME = u'site_community_1'

        try:
            with mock_dataserver.mock_db_trans(self.ds):
                c1 = Community.create_community(username=u'site_community_1')
                c2 = Community.create_community(username=u'site_community_2')
                # To keep our dependencies clean, we explicitly set this
                # rather than import SiteCommunity from nti.app.site
                ISiteCommunity.providedBy(c1)
                ISiteCommunity.providedBy(c2)

                for username in (u'test001', u'test002'):
                    user = User.get_user(username)
                    user.record_dynamic_membership(c2)

            gsm.registerUtility(TestPolicy, ISitePolicyUserEventListener)

            # Test users are added to site community and not removed from others
            self.testapp.post_json('/dataserver2/@@reset_site_community',
                                   {'usernames': 'test001,test002'},
                                   extra_environ=self._make_extra_environ(user=u'admin001@nextthought.com'),
                                   status=200)
            with mock_dataserver.mock_db_trans(self.ds):
                for username in (u'test001', u'test002'):
                    user = User.get_user(username)
                    assert_that(user, is_in(c1))
                    assert_that(user, is_in(c2))

            # Test users are removed from others
            self.testapp.post_json('/dataserver2/@@reset_site_community?remove_all_others=True',
                                   {'usernames': 'test001,test002'},
                                   extra_environ=self._make_extra_environ(user=u'admin001@nextthought.com'),
                                   status=200)
            with mock_dataserver.mock_db_trans(self.ds):
                for username in (u'test001', u'test002'):
                    user = User.get_user(username)
                    assert_that(user, is_in(c1))
                    assert_that(user, not is_in(c2))

            with mock_dataserver.mock_db_trans(self.ds):
                for username in (u'test001', u'test002'):
                    user = User.get_user(username)
                    user.record_dynamic_membership(c2)
                    user.record_no_longer_dynamic_member(c1)

            # Test all site users are updated
            self.testapp.post_json('/dataserver2/@@reset_site_community?remove_all_others=True&all=True',
                                   extra_environ=self._make_extra_environ(user=u'admin001@nextthought.com'),
                                   status=200)
            with mock_dataserver.mock_db_trans(self.ds):
                for username in (u'test001', u'test002'):
                    user = User.get_user(username)
                    assert_that(user, is_in(c1))
                    assert_that(user, not is_in(c2))

        finally:
            gsm.unregisterUtility(TestPolicy, ISitePolicyUserEventListener)


    def _assert_user_creation_site(self, siteOne='beta.nextthought.com', siteTwo=none()):
        with mock_dataserver.mock_db_trans(self.ds, site_name='alpha.nextthought.com'):
            cs_user = self._get_user('creationsiteuser')
            assert_that(get_user_creation_sitename(cs_user), is_(siteOne))

            ncs_user = self._get_user('nocreationsiteuser')
            assert_that(get_user_creation_sitename(ncs_user), is_(siteTwo))

    @WithSharedApplicationMockDS(users=(u'nocreationsiteuser',
                                        u'creationsiteuser'),
                                 testapp=True,
                                 default_authenticate=True)
    def test_set_user_creation_site_in_site(self):
        environ = self._make_extra_environ()
        environ['HTTP_ORIGIN'] = 'https://alpha.nextthought.com'
        url = '/dataserver2/@@SetUserCreationSiteInSite'

        with mock_dataserver.mock_db_trans(self.ds, site_name='alpha.nextthought.com'):
            cs_user = self._get_user('creationsiteuser')
            set_user_creation_site(cs_user, 'beta.nextthought.com')
            # If we created a user through a view rather than db trans this comm would get created
            site_comm = Community.get_community('testing_community')
            if site_comm is None:
                site_comm = Community.create_community(username='testing_community')
            for username in ('nocreationsiteuser', 'creationsiteuser'):
                user = self._get_user(username)
                user.record_dynamic_membership(site_comm)

        # Check no commit
        self.testapp.post_json(url, {'commit': 'false'}, status=200, extra_environ=environ)
        self._assert_user_creation_site(siteOne='beta.nextthought.com', siteTwo=none())

        self.testapp.post_json(url, {'commit': False}, status=200, extra_environ=environ)
        self._assert_user_creation_site(siteOne='beta.nextthought.com', siteTwo=none())

        # Check commit
        self.testapp.post_json(url, {'commit': 'true'}, status=200, extra_environ=environ)
        self._assert_user_creation_site(siteOne='beta.nextthought.com', siteTwo='alpha.nextthought.com')

        # Check force
        self.testapp.post_json(url, {'force': True, 'commit': None}, status=200, extra_environ=environ)
        self._assert_user_creation_site(siteOne='beta.nextthought.com', siteTwo='alpha.nextthought.com')

        self.testapp.post_json(url, {'force': True, 'commit': 'Y'}, status=200, extra_environ=environ)
        self._assert_user_creation_site(siteOne='alpha.nextthought.com', siteTwo='alpha.nextthought.com')

    @WithSharedApplicationMockDS(users=True, testapp=True, default_authenticate=True)
    def test_set_entity_creation_site(self):
        sitename = u'demo.nextthought.com'
        sitename2 = 'alpha.nextthought.com'
        username = u'user001'
        communityname = u'community001'
        groupname = u'group001'
        with mock_dataserver.mock_db_trans(self.ds):
            user = User.create_user(username=username)
            assert_that(get_entity_creation_sitename(user), is_(None))

            community = Community.create_community(username=communityname)
            assert_that(get_entity_creation_sitename(community), is_(None))

            dfl = DynamicFriendsList(username=groupname)
            dfl.creator = user
            user.addContainedObject(dfl)
            groupID = dfl.NTIID
            assert_that(get_entity_creation_sitename(dfl), is_(None))

        # user
        result = self.testapp.post_json('/dataserver2/@@SetEntityCreationSite', {'entityId': username, 'site': 'invalid_site'}, status=422).json_body
        assert_that(result['message'], is_('Invalid site.'))
        self.testapp.post_json('/dataserver2/@@SetEntityCreationSite', {'entityId': username, 'site': sitename}, status=204)
        with mock_dataserver.mock_db_trans(self.ds):
            assert_that(get_entity_creation_sitename(user), is_(sitename))

        self.testapp.post_json('/dataserver2/@@SetEntityCreationSite', {'entityId': username, 'site': sitename2}, status=204)
        with mock_dataserver.mock_db_trans(self.ds):
            assert_that(get_entity_creation_sitename(user), is_(sitename2))

        # community
        self.testapp.post_json('/dataserver2/@@SetEntityCreationSite', {'entityId': communityname, 'site': 'invalid_site'}, status=422)
        self.testapp.post_json('/dataserver2/@@SetEntityCreationSite', {'entityId': communityname, 'site': sitename}, status=204)
        with mock_dataserver.mock_db_trans(self.ds):
            assert_that(get_entity_creation_sitename(community), is_(sitename))

        self.testapp.post_json('/dataserver2/@@SetEntityCreationSite', {'entityId': communityname, 'site': sitename2}, status=204)
        with mock_dataserver.mock_db_trans(self.ds):
            assert_that(get_entity_creation_sitename(community), is_(sitename2))

        # group
        self.testapp.post_json('/dataserver2/@@SetEntityCreationSite', {'entityId': groupID, 'site': 'invalid_site'}, status=422)
        self.testapp.post_json('/dataserver2/@@SetEntityCreationSite', {'entityId': groupID, 'site': sitename}, status=204)
        with mock_dataserver.mock_db_trans(self.ds):
            assert_that(get_entity_creation_sitename(dfl), is_(sitename))

        self.testapp.post_json('/dataserver2/@@SetEntityCreationSite', {'entityId': groupID, 'site': sitename2}, status=204)
        with mock_dataserver.mock_db_trans(self.ds):
            assert_that(get_entity_creation_sitename(dfl), is_(sitename2))

        # reset
        self.testapp.post_json('/dataserver2/@@SetEntityCreationSite', {'entityId': username}, status=204)
        self.testapp.post_json('/dataserver2/@@set_entity_creation_site', {'entityId': communityname, 'site': 'dataserver2'}, status=204)
        self.testapp.post_json('/dataserver2/@@SetEntityCreationSite', {'entityId': groupID, 'site': 'dataserver2'}, status=204)
        with mock_dataserver.mock_db_trans(self.ds):
            assert_that(get_entity_creation_sitename(user), is_(None))
            assert_that(get_entity_creation_sitename(community), is_(None))
            assert_that(get_entity_creation_sitename(dfl), is_(None))

        # validate parameters
        result = self.testapp.post_json('/dataserver2/@@SetEntityCreationSite', {'site': 'dataserver2'}, status=422).json_body
        assert_that(result['message'], 'Must specify a entityId.')

        result = self.testapp.post_json('/dataserver2/@@SetEntityCreationSite', {'entityid': 'invalid_entity_id','site': 'dataserver2'}, status=422).json_body
        assert_that(result['message'], 'Invalid entityId.')
