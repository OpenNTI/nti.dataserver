#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import fudge

from hamcrest import assert_that
from hamcrest import calling
from hamcrest import has_length
from hamcrest import is_
from hamcrest import not_
from hamcrest import none
from hamcrest import raises

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

from nti.app.authentication.interfaces import ISiteAuthentication

from nti.app.authentication.subscribers import install_site_authentication

from nti.app.authentication.tests import AuthenticationLayerTest

from nti.app.authentication._zope_authentication import SiteAuthentication

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

    @mock_dataserver.WithMockDS
    def test_get_principal(self):

        with mock_db_trans(self.ds):
            synchronize_host_policies()

            # Ensure authentication utils are present
            test_base_site = get_site_for_site_names(('test.nextthought.com',))
            base_utils = self.get_authentication_utils(test_base_site)
            assert_that(base_utils, has_length(1))

            test_child_site = get_site_for_site_names(('test-child.nextthought.com',))
            child_utils = self.get_authentication_utils(test_child_site)
            assert_that(child_utils, has_length(1))

            ds_auth = component.getUtility(IAuthentication)
            assert_that(ds_auth, not_(none()))

            # Set up some users in our test sites
            self._create_user('siteless-one')

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
