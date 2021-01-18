#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import base64

from nti.dataserver.authorization import ROLE_ADMIN
from zope.security.management import setSecurityPolicy
from zope.securitypolicy.interfaces import IPrincipalRoleManager
from zope.securitypolicy.zopepolicy import ZopeSecurityPolicy

if 'encodebytes' in base64.__dict__:  # pragma NO COVER Python >= 3.0
    encodebytes = base64.encodebytes
else:  # pragma NO COVER Python < 3.0
    encodebytes = base64.encodestring

import contextlib

import fudge

from hamcrest import assert_that
from hamcrest import calling
from hamcrest import has_length
from hamcrest import has_property
from hamcrest import is_
from hamcrest import not_
from hamcrest import none
from hamcrest import raises

from pyramid.request import Request

from repoze.who.interfaces import IAPIFactory

from z3c.baseregistry.baseregistry import BaseComponents

from zope import component

from zope.authentication.interfaces import IAuthentication
from zope.authentication.interfaces import PrincipalLookupError

from zope.component import globalSiteManager as BASE

from zope.component.hooks import site

from zope.interface.interfaces import IComponents

from zope.location.interfaces import IContained

from zope.principalregistry.principalregistry import PrincipalRegistry

from zope.site.interfaces import INewLocalSite

from nti.app.authentication._zope_authentication import SiteAuthentication

from nti.app.authentication.interfaces import ISiteAuthentication

from nti.app.authentication.subscribers import install_site_authentication

from nti.app.authentication.tests import AuthenticationLayerTest

from nti.app.authentication.who_apifactory import create_who_apifactory

from nti.appserver.policies.sites import BASEADULT

from nti.dataserver.tests import mock_dataserver

from nti.dataserver.tests.mock_dataserver import mock_db_trans

from nti.dataserver.users import User

from nti.dataserver.users.common import set_user_creation_site

from nti.site.hostpolicy import synchronize_host_policies

from nti.site.interfaces import IHostPolicySiteManager

from nti.site.site import get_site_for_site_names

from nti.testing.matchers import validly_provides

__docformat__ = "restructuredtext en"

TEST_BASE = BaseComponents(BASEADULT,
                       name='test.nextthought.com',
                       bases=(BASEADULT,))

TEST_CHILD = BaseComponents(TEST_BASE,
                             name='test-child.nextthought.com',
                             bases=(TEST_BASE,))

SITES = (TEST_BASE,
         TEST_CHILD)


class TestZopeAuthentication(AuthenticationLayerTest):

    def setUp(self):
        super(TestZopeAuthentication, self).setUp()
        for bc in SITES:
            bc.__init__(bc.__parent__, name=bc.__name__, bases=bc.__bases__)
            BASE.registerUtility(bc, name=bc.__name__, provided=IComponents)
        BASE.registerHandler(install_site_authentication, required=(IHostPolicySiteManager, INewLocalSite))

    def tearDown(self):
        for bc in SITES:
            BASE.unregisterUtility(bc, name=bc.__name__, provided=IComponents)
        BASE.registerHandler(install_site_authentication, (IHostPolicySiteManager, INewLocalSite))
        super(TestZopeAuthentication, self).tearDown()

    def get_authentication_utils(self, site):
        sm = site.getSiteManager()
        authentication_utils = [reg for reg in sm.registeredUtilities()
                                if (reg.provided.isOrExtends(IAuthentication)
                                    and reg.name == '')]
        return authentication_utils

    def _create_user(self, username, password=u'temp001'):
        return User.create_user(self.ds, username=username,
                                password=password)

    def test_site_authentication(self):
        assert_that(SiteAuthentication(), validly_provides(ISiteAuthentication, IContained))

    def _setup_sites(self):
        synchronize_host_policies()

        # Ensure authentication utils are present
        test_base_site = get_site_for_site_names(('test.nextthought.com',))
        base_utils = self.get_authentication_utils(test_base_site)
        assert_that(base_utils, has_length(1))

        test_child_site = get_site_for_site_names(('test-child.nextthought.com',))
        child_utils = self.get_authentication_utils(test_child_site)
        assert_that(child_utils, has_length(1))

        return test_base_site, test_child_site

    @mock_dataserver.WithMockDSTrans
    def test_get_principal(self):

        with _security_policy_context(ZopeSecurityPolicy):
            test_base_site, test_child_site = self._setup_sites()

            ds_auth = component.getUtility(IAuthentication)
            assert_that(ds_auth, not_(none()))

            # Set up some users in our test sites
            self._create_user('siteless-one')

            # An nti admin should always be returned, even if created
            # in another site
            base_user = self._create_user('test-nti-admin')
            ds_folder = self.ds.dataserver_folder
            ds_role_manager = IPrincipalRoleManager(ds_folder)
            ds_role_manager.assignRoleToPrincipal(ROLE_ADMIN.id,
                                                  base_user.username)
            set_user_creation_site(base_user, 'nti.nextthought.com')

            base_user = self._create_user('test-one')
            set_user_creation_site(base_user, 'test.nextthought.com')

            child_user = self._create_user('test-child-one')
            set_user_creation_site(child_user, 'test-child.nextthought.com')

            # Validate we can only get principals from auth utils in appropriate sites

            #   First, global registry
            auth = component.getUtility(IAuthentication)
            auth.definePrincipal('registered-principal',
                                 'Registered Principal')

            assert_that(auth, is_(PrincipalRegistry))
            assert_that(calling(auth.getPrincipal).with_args('test-nonuser'),
                        raises(PrincipalLookupError))
            assert_that(calling(auth.getPrincipal).with_args('siteless-one'),
                        raises(PrincipalLookupError))
            assert_that(calling(auth.getPrincipal).with_args('test-nti-admin'),
                        raises(PrincipalLookupError))
            assert_that(calling(auth.getPrincipal).with_args('test-one'),
                        raises(PrincipalLookupError))
            assert_that(calling(auth.getPrincipal).with_args('test-child-one'),
                        raises(PrincipalLookupError))
            assert_that(auth.getPrincipal('registered-principal').id,
                        is_('registered-principal'))

            with site(test_base_site):
                auth = component.getUtility(IAuthentication)
                assert_that(auth, is_(SiteAuthentication))
                assert_that(auth.getPrincipal('siteless-one').id, is_('siteless-one'))
                assert_that(auth.getPrincipal('test-nti-admin').id, is_('test-nti-admin'))
                assert_that(auth.getPrincipal('test-one').id, is_('test-one'))
                assert_that(calling(auth.getPrincipal).with_args('test-child-one'),
                            raises(PrincipalLookupError))
                assert_that(calling(auth.getPrincipal).with_args('test-nonuser'),
                            raises(PrincipalLookupError))
                assert_that(auth.getPrincipal('registered-principal').id,
                            is_('registered-principal'))

            with site(test_child_site):
                auth = component.getUtility(IAuthentication)
                assert_that(auth, is_(SiteAuthentication))
                assert_that(auth.getPrincipal('siteless-one').id, is_('siteless-one'))
                assert_that(auth.getPrincipal('test-nti-admin').id, is_('test-nti-admin'))
                assert_that(auth.getPrincipal('test-one').id, is_('test-one'))
                assert_that(auth.getPrincipal('test-child-one').id, is_('test-child-one'))
                assert_that(calling(auth.getPrincipal).with_args('test-nonuser'),
                            raises(PrincipalLookupError))
                assert_that(auth.getPrincipal('registered-principal').id,
                            is_('registered-principal'))

    @mock_dataserver.WithMockDS
    @fudge.patch("nti.app.authentication._zope_authentication.SiteAuthentication._query_next_util")
    def test_get_principal_no_next_util(self, query_next_util):
        # A configuration where the site authentication utility has
        # no utility to delegate to and doesn't find a user itself.
        query_next_util.is_callable().returns(None)

        with mock_db_trans(self.ds):
            synchronize_host_policies()

            test_base_site = get_site_for_site_names(('test.nextthought.com',))
            with site(test_base_site):
                auth = component.getUtility(IAuthentication)
                assert_that(auth, is_(SiteAuthentication))
                assert_that(calling(auth.getPrincipal).with_args('test-nonuser'),
                            raises(PrincipalLookupError))

    @mock_dataserver.WithMockDS
    @fudge.patch("nti.app.authentication._zope_authentication.SiteAuthentication._query_next_util")
    def test_get_principal_no_next_util(self, query_next_util):
        # A configuration where the site authentication utility has
        # no utility to delegate to and doesn't find a user itself.
        query_next_util.is_callable().returns(None)

        with mock_db_trans(self.ds):
            synchronize_host_policies()

            test_base_site = get_site_for_site_names(('test.nextthought.com',))
            with site(test_base_site):
                auth = component.getUtility(IAuthentication)
                assert_that(auth, is_(SiteAuthentication))
                assert_that(calling(auth.getPrincipal).with_args('test-nonuser'),
                            raises(PrincipalLookupError))

    def _who_api_factory(self, auth_response):
        mock_who_api = fudge.Fake('who_api')
        mock_who_api.provides('authenticate').returns(auth_response)
        mock_who_api_factory = fudge.Fake('who_api_factory')
        mock_who_api_factory.is_callable().returns(mock_who_api)

        return mock_who_api_factory

    @mock_dataserver.WithMockDSTrans
    def test_authenticate_none(self):
        mock_who_api_factory = self._who_api_factory(auth_response=None)
        with _provide_utility(mock_who_api_factory, IAPIFactory):
            request = Request.blank('/')
            result = SiteAuthentication().authenticate(request)

            assert_that(result, is_(none()))

    @mock_dataserver.WithMockDSTrans
    def test_authenticate_no_userid(self):
        mock_who_api_factory = self._who_api_factory(auth_response={})
        with _provide_utility(mock_who_api_factory, IAPIFactory):
            request = Request.blank('/')
            result = SiteAuthentication().authenticate(request)

            assert_that(result, is_(none()))

    def _authd_req(self, username, password=u'temp001'):
        value = encodebytes(b'%s:%s' % (username, password)).decode('ascii')
        return Request.blank('/',
                             environ={
                                 'HTTP_AUTHORIZATION': 'Basic %s' % value
                             })

    def assert_auth(self, auth, username):
        assert_that(auth.authenticate(self._authd_req(username)),
                    has_property('id', username))

    def assert_no_auth(self, auth, username):
        assert_that(auth.authenticate(self._authd_req(username)), is_(none()))

    @mock_dataserver.WithMockDSTrans
    def test_authenticate(self):

        test_base_site, test_child_site = self._setup_sites()

        ds_auth = component.getUtility(IAuthentication)
        assert_that(ds_auth, not_(none()))

        # Set up some users in our test sites
        self._create_user('siteless-one')

        global_user = self._create_user('global-registered-one')
        auth = component.getUtility(IAuthentication)
        assert_that(auth, is_(PrincipalRegistry))
        principal_registry = auth
        principal_registry.definePrincipal(global_user.username,
                                           'Registered Principal',
                                           login='global-registered-one',
                                           password=b'temp001')

        base_user = self._create_user('test-one')
        set_user_creation_site(base_user, 'test.nextthought.com')

        child_user = self._create_user('test-child-one')
        set_user_creation_site(child_user, 'test-child.nextthought.com')

        mock_who_api_factory = create_who_apifactory()
        with _provide_utility(mock_who_api_factory, IAPIFactory):
            # Validate we can only get principals from auth utils in appropriate sites

            #   First, global registry
            self.assert_auth(auth, 'global-registered-one')
            self.assert_no_auth(auth, 'siteless-one')
            self.assert_no_auth(auth, 'test-one')
            self.assert_no_auth(auth, 'test-child-one')
            self.assert_no_auth(auth, 'test-nonuser')

            with site(test_base_site):
                auth = component.getUtility(IAuthentication)
                assert_that(auth, is_(SiteAuthentication))
                self.assert_auth(auth, 'global-registered-one')
                self.assert_auth(auth, 'siteless-one')
                self.assert_auth(auth, 'test-one')
                self.assert_no_auth(auth, 'test-child-one')
                self.assert_no_auth(auth, 'test-nonuser')

            with site(test_child_site):
                auth = component.getUtility(IAuthentication)
                assert_that(auth, is_(SiteAuthentication))
                self.assert_auth(auth, 'global-registered-one')
                self.assert_auth(auth, 'siteless-one')
                self.assert_auth(auth, 'test-one')
                self.assert_auth(auth, 'test-child-one')
                self.assert_no_auth(auth, 'test-nonuser')


@contextlib.contextmanager
def _provide_utility(util, provided):
    gsm = component.getGlobalSiteManager()

    old_util = component.queryUtility(provided)
    gsm.registerUtility(util, provided)
    try:
        yield
    finally:
        gsm.unregisterUtility(util, provided)
        gsm.registerUtility(old_util, provided)


@contextlib.contextmanager
def _security_policy_context(new_policy):
    old_security_policy = setSecurityPolicy(new_policy)
    try:
        yield
    finally:
        setSecurityPolicy(old_security_policy)
