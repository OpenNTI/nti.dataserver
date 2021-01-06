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

from zope.site.interfaces import INewLocalSite

from nti.app.authentication import _DSAuthentication

from nti.app.authentication.subscribers import on_site_created

from nti.app.authentication.tests import AuthenticationLayerTest

from nti.app.authentication.zope_authentication import _SiteAuthentication

from nti.appserver.policies.sites import BASEADULT

from nti.dataserver.tests import mock_dataserver

from nti.dataserver.tests.mock_dataserver import mock_db_trans

from nti.dataserver.users import User

from nti.dataserver.users.common import set_user_creation_site

from nti.site.hostpolicy import synchronize_host_policies

from nti.site.interfaces import IHostPolicySiteManager

from nti.site.site import get_site_for_site_names

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
        BASE.registerHandler(on_site_created, required=(IHostPolicySiteManager, INewLocalSite))

    def tearDown(self):
        for bc in SITES:
            BASE.unregisterUtility(bc, name=bc.__name__, provided=IComponents)
        BASE.registerHandler(on_site_created, (IHostPolicySiteManager, INewLocalSite))
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

            #   First, DS site
            auth = component.getUtility(IAuthentication)
            assert_that(auth, is_(_DSAuthentication))
            assert_that(auth.getPrincipal('siteless-one').id, is_('siteless-one'))
            assert_that(auth.getPrincipal('test-one').id, is_('test-one'))
            assert_that(auth.getPrincipal('test-child-one').id, is_('test-child-one'))
            assert_that(calling(auth.getPrincipal).with_args('test-nonuser'),
                        raises(PrincipalLookupError))

            with site(test_base_site):
                auth = component.getUtility(IAuthentication)
                assert_that(auth, is_(_SiteAuthentication))
                assert_that(auth.getPrincipal('siteless-one').id, is_('siteless-one'))
                assert_that(auth.getPrincipal('test-one').id, is_('test-one'))
                assert_that(calling(auth.getPrincipal).with_args('test-child-one'),
                            raises(PrincipalLookupError))
                assert_that(calling(auth.getPrincipal).with_args('test-nonuser'),
                            raises(PrincipalLookupError))

            with site(test_child_site):
                auth = component.getUtility(IAuthentication)
                assert_that(auth, is_(_SiteAuthentication))
                assert_that(auth.getPrincipal('siteless-one').id, is_('siteless-one'))
                assert_that(auth.getPrincipal('test-one').id, is_('test-one'))
                assert_that(auth.getPrincipal('test-child-one').id, is_('test-child-one'))
                assert_that(calling(auth.getPrincipal).with_args('test-nonuser'),
                            raises(PrincipalLookupError))

    @mock_dataserver.WithMockDS
    @fudge.patch("nti.app.authentication.zope_authentication._SiteAuthentication._query_next_util")
    def test_get_principal_no_next_util(self, query_next_util):
        # A configuration where the site authentication utility has
        # no utility to delegate to and doesn't find a user itself.
        query_next_util.is_callable().returns(None)

        with mock_db_trans(self.ds):
            synchronize_host_policies()

            test_base_site = get_site_for_site_names(('test.nextthought.com',))
            with site(test_base_site):
                auth = component.getUtility(IAuthentication)
                assert_that(auth, is_(_SiteAuthentication))
                assert_that(calling(auth.getPrincipal).with_args('test-nonuser'),
                            raises(PrincipalLookupError))

    @mock_dataserver.WithMockDS
    @fudge.patch("nti.app.authentication.zope_authentication._SiteAuthentication._query_next_util")
    def test_get_principal_no_next_util(self, query_next_util):
        # A configuration where the site authentication utility has
        # no utility to delegate to and doesn't find a user itself.
        query_next_util.is_callable().returns(None)

        with mock_db_trans(self.ds):
            synchronize_host_policies()

            test_base_site = get_site_for_site_names(('test.nextthought.com',))
            with site(test_base_site):
                auth = component.getUtility(IAuthentication)
                assert_that(auth, is_(_SiteAuthentication))
                assert_that(calling(auth.getPrincipal).with_args('test-nonuser'),
                            raises(PrincipalLookupError))
