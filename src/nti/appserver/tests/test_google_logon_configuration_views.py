#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from hamcrest import assert_that
from hamcrest import has_entries
from hamcrest import has_length
from hamcrest import has_properties
from hamcrest import instance_of
from hamcrest import is_
from hamcrest import none
from hamcrest import not_none
from hamcrest import same_instance

from pyramid.interfaces import IRequest

from zope import component
from zope import interface
from zope import lifecycleevent

from zope.component.hooks import getSite

from zope.event import notify

from nti.appserver.interfaces import ILogonLinkProvider
from nti.appserver.interfaces import IUnauthenticatedUserLinkProvider
from nti.appserver.interfaces import IGoogleLogonLookupUtility
from nti.appserver.interfaces import IGoogleLogonSettings

from nti.appserver.logon import GOOGLE_OAUTH_EXTERNAL_ID_TYPE
from nti.appserver.logon import GoogleLogonSettings
from nti.appserver.logon import GoogleLogonLookupUtility
from nti.appserver.logon import SimpleUnauthenticatedUserGoogleLinkProvider
from nti.appserver.logon import SimpleMissingUserGoogleLinkProvider
from nti.appserver.logon import DefaultGoogleLogonLookupUtility

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.coremetadata.interfaces import IMissingUser

from nti.dataserver.tests import mock_dataserver

from nti.dataserver.users import User

from nti.dataserver.users.common import remove_user_creation_site
from nti.dataserver.users.common import set_user_creation_site
from nti.dataserver.users.common import user_creation_sitename

from nti.externalization.interfaces import ObjectModifiedFromExternalEvent

from nti.identifiers.interfaces import IUserExternalIdentityContainer

from nti.identifiers.utils import get_user_for_external_id

__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


class TestGoogleLogonConfigurationViews(ApplicationLayerTest):

    def _assert_enabled(self, lookup_by_email=False, restricted_domain=None):
        with mock_dataserver.mock_db_trans(self.ds, site_name='demo.nextthought.com'):
            site_manager = getSite().getSiteManager()

            # lookup
            lookup = component.getUtility(IGoogleLogonLookupUtility)
            assert_that(lookup, instance_of(GoogleLogonLookupUtility))
            assert_that(lookup.__parent__, same_instance(site_manager))
            assert_that(lookup.lookup_by_email, is_(lookup_by_email))

            # settings
            settings = component.getUtility(IGoogleLogonSettings)
            assert_that(settings, instance_of(GoogleLogonSettings))
            assert_that(settings.__parent__, same_instance(site_manager))
            assert_that(settings.hd, is_(restricted_domain))

            subs = [x for x in site_manager.registeredSubscriptionAdapters()]
            assert_that(subs, has_length(2))

    def _assert_disabled(self):
        with mock_dataserver.mock_db_trans(self.ds, site_name='demo.nextthought.com'):
            site_manager = getSite().getSiteManager()

            # we have a global default one.
            lookup = component.getUtility(IGoogleLogonLookupUtility)
            assert_that(lookup, instance_of(DefaultGoogleLogonLookupUtility))

            settings = component.queryUtility(IGoogleLogonSettings)
            assert_that(settings, is_(None))

            subs = [x for x in site_manager.registeredSubscriptionAdapters()]
            assert_that(subs, has_length(0))

    @WithSharedApplicationMockDS(users=(u'user001', u'admin001@nextthought.com'), testapp=True, default_authenticate=False)
    def test_enable_and_disable(self):
        extra_environ = self._make_extra_environ(username=u'admin001@nextthought.com')

        # enable
        enable_base_url = 'https://demo.nextthought.com/dataserver2/@@enable_google_logon'
        self.testapp.post_json(enable_base_url, status=401, extra_environ=self._make_extra_environ(username=None))
        self.testapp.post_json(enable_base_url, status=403, extra_environ=self._make_extra_environ(username=u'user001'))

        res = self.testapp.post_json(enable_base_url, status=200, extra_environ=extra_environ)
        self._assert_enabled()

        enable_url = "%s?lookup_by_email=%s&restricted_domain=%s" % (enable_base_url, 'true', 'abc')
        res = self.testapp.post_json(enable_url, status=200, extra_environ=extra_environ)
        self._assert_enabled(True, 'abc')

        enable_url = "%s?lookup_by_email=%s&restricted_domain=%s" % (enable_base_url, 'false', '')
        res = self.testapp.post_json(enable_url, status=200, extra_environ=extra_environ)
        self._assert_enabled(False, None)

        # disable
        disable_url = 'https://demo.nextthought.com/dataserver2/@@disable_google_logon'
        self.testapp.post_json(disable_url, status=401, extra_environ=self._make_extra_environ(username=None))
        self.testapp.post_json(disable_url, status=403, extra_environ=self._make_extra_environ(username=u'user001'))
        self.testapp.post_json(disable_url, status=204, extra_environ=extra_environ)
        self._assert_disabled()

        # disable again
        res = self.testapp.post_json(disable_url, status=204, extra_environ=extra_environ)
        self._assert_disabled()

    @WithSharedApplicationMockDS(users=(u'user001', u'test@gmail.com'), testapp=True, default_authenticate=False)
    def testGoogleLogonLookupUtility(self):
        with mock_dataserver.mock_db_trans(self.ds, site_name='demo.nextthought.com'):
            gmail = u'test@gmail.com'
            gmail2 = u'test2@gmail.com'

            user = User.get_user('user001')
            assert_that(user, not_none())
            _set_external_id(user, gmail2)

            lookup = GoogleLogonLookupUtility()
            assert_that(lookup.lookup_user(gmail), is_(None))
            assert_that(lookup.lookup_user(gmail2), same_instance(user))

            lookup.lookup_by_email = True
            user = User.get_user(gmail)
            assert_that(user, not_none())
            assert_that(lookup.lookup_user(gmail), same_instance(user))
            assert_that(lookup.lookup_user(gmail2), is_(None))


def _set_external_id(user, email):
    id_container = IUserExternalIdentityContainer(user)
    id_container.add_external_mapping(GOOGLE_OAUTH_EXTERNAL_ID_TYPE, email)
    notify(ObjectModifiedFromExternalEvent(user))


def _user_with_external_id(email):
    return get_user_for_external_id(GOOGLE_OAUTH_EXTERNAL_ID_TYPE, email)


class TestIdentifiers(ApplicationLayerTest):

    @WithSharedApplicationMockDS(users=(u'user001', u'user002', u'user003', u'user004', u'user005'), testapp=True, default_authenticate=False)
    def test_get_user_for_external_id(self):
        # If user logs in child site and then logs in the parent site, it would create two accounts for the user.
        # If there are two accounts for the same user, we would prefer the one from the current site.
        # Log in child first
        gmail = u'test@gmail.com'
        with mock_dataserver.mock_db_trans(self.ds, site_name='demo.dev'):
            assert_that(_user_with_external_id(gmail), is_(None))
            user1 = User.get_user('user001')
            _set_external_id(user1, gmail)
            assert_that(_user_with_external_id(gmail), same_instance(user1))

        with mock_dataserver.mock_db_trans(self.ds, site_name='eval.nextthought.com'):
            assert_that(_user_with_external_id(gmail), is_(None))
            user2 = User.get_user('user002')
            _set_external_id(user2, gmail)
            assert_that(_user_with_external_id(gmail), same_instance(user2))

        with mock_dataserver.mock_db_trans(self.ds, site_name='demo.dev'):
            # find user in current site.
            assert_that(_user_with_external_id(gmail), is_(user1))

        with mock_dataserver.mock_db_trans(self.ds, site_name='demo.nextthought.com'):
            # find user in parent site
            assert_that(_user_with_external_id(gmail), is_(user2))

        with mock_dataserver.mock_db_trans(self.ds, site_name='demo-alpha.nextthought.com'):
            # find user in grand parent site
            assert_that(_user_with_external_id(gmail), is_(user2))

        # Log in parent first.
        gmail = u'test2@gmail.com'
        with mock_dataserver.mock_db_trans(self.ds, site_name='eval.nextthought.com'):
            assert_that(_user_with_external_id(gmail), is_(None))
            user3 = User.get_user('user003')
            _set_external_id(user3, gmail)
            assert_that(_user_with_external_id(gmail), same_instance(user3))

        with mock_dataserver.mock_db_trans(self.ds, site_name='demo.nextthought.com'):
            # find user in parent site
            assert_that(_user_with_external_id(gmail), same_instance(user3))

        with mock_dataserver.mock_db_trans(self.ds, site_name='demo.dev'):
            # find user in grand parent site
            assert_that(_user_with_external_id(gmail), same_instance(user3))

        with mock_dataserver.mock_db_trans(self.ds, site_name='demo-alpha.nextthought.com'):
            # find user in grand parent site
            assert_that(_user_with_external_id(gmail), same_instance(user3))

        # Same gmail in different sites.
        gmail = u'test3@gmail.com'
        with mock_dataserver.mock_db_trans(self.ds, site_name='alpha.nextthought.com'):
            assert_that(_user_with_external_id(gmail), is_(None))
            user4 = User.get_user('user004')
            _set_external_id(user4, gmail)
            assert_that(_user_with_external_id(gmail), same_instance(user4))

        with mock_dataserver.mock_db_trans(self.ds, site_name='demo.nextthought.com'):
            assert_that(_user_with_external_id(gmail), is_(None))
            user5 = User.get_user('user005')
            _set_external_id(user5, gmail)
            assert_that(_user_with_external_id(gmail), same_instance(user5))

        with mock_dataserver.mock_db_trans(self.ds, site_name='alpha.dev'):
            assert_that(_user_with_external_id(gmail), same_instance(user4))

        with mock_dataserver.mock_db_trans(self.ds, site_name='demo.dev'):
            assert_that(_user_with_external_id(gmail), same_instance(user5))
