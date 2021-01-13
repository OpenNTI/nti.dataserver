#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import fudge

from hamcrest import assert_that
from hamcrest import has_length
from hamcrest import is_
from hamcrest import none
from hamcrest import not_
from hamcrest import same_instance

from z3c.baseregistry.baseregistry import BaseComponents

from zope.app.appsetup.bootstrap import ensureUtility

from zope.authentication.interfaces import IAuthentication

from zope.component import globalSiteManager as BASE

from zope.interface.interfaces import IComponents

from zope.site.interfaces import INewLocalSite

from nti.app.authentication.subscribers import install_site_authentication

from nti.appserver.policies.sites import BASEADULT

from nti.dataserver.generations.evolve112 import do_evolve

from nti.dataserver.tests import mock_dataserver

from nti.dataserver.tests.mock_dataserver import mock_db_trans

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


class TestEvolve112(mock_dataserver.DataserverLayerTest):

    def setUp(self):
        super(TestEvolve112, self).setUp()
        for bc in SITES:
            bc.__init__(bc.__parent__, name=bc.__name__, bases=bc.__bases__)
            BASE.registerUtility(bc, name=bc.__name__, provided=IComponents)

        # We want to test sites that were created prior to this handler
        # being in place, so disable it for the test
        BASE.unregisterHandler(install_site_authentication, (IHostPolicySiteManager, INewLocalSite))

    def tearDown(self):
        for bc in SITES:
            BASE.unregisterUtility(bc, name=bc.__name__, provided=IComponents)
        BASE.registerHandler(install_site_authentication, (IHostPolicySiteManager, INewLocalSite))
        super(TestEvolve112, self).tearDown()

    def get_authentication_utils(self, site):
        sm = site.getSiteManager()
        authentication_utils = [reg for reg in sm.registeredUtilities()
                                if (reg.provided.isOrExtends(IAuthentication)
                                    and reg.name == '')]
        return authentication_utils

    def install_ds_zope_authentication(self, dataserver_folder):
        from nti.app.authentication import _DSAuthentication
        ensureUtility(dataserver_folder,
                      IAuthentication,
                      'authentication',
                      _DSAuthentication)

    def _test_evolve(self, add_ds_util=True):

        with mock_db_trans(self.ds) as conn:
            context = fudge.Fake().has_attr(connection=conn)
            synchronize_host_policies()

            ds_folder = self.ds.dataserver_folder
            if add_ds_util:
                self.install_ds_zope_authentication(ds_folder)

            ds_utils = self.get_authentication_utils(ds_folder)
            ds_sm = ds_folder.getSiteManager()

            # Verify expected state
            if add_ds_util:
                assert_that(ds_utils, has_length(1))
                assert_that(ds_sm.get('default', {}).get('authentication'),
                            not_(none()))
            else:
                assert_that(ds_utils, has_length(0))
                assert_that(ds_sm.get('default', {}).get('authentication'),
                            is_(none()))

            # Verify we don't have the util yet
            test_base_site = get_site_for_site_names(('test.nextthought.com',))
            base_utils = self.get_authentication_utils(test_base_site)
            assert_that(base_utils, has_length(0))
            test_base_sm = test_base_site.getSiteManager()
            assert_that(test_base_sm.get('default', {}).get('authentication'),
                        is_(none()))

            test_child_site = get_site_for_site_names(('test-child.nextthought.com',))
            child_utils = self.get_authentication_utils(test_child_site)
            assert_that(child_utils, has_length(0))
            test_child_sm = test_child_site.getSiteManager()
            assert_that(test_child_sm.get('default', {}).get('authentication'),
                        is_(none()))

            do_evolve(context)

            # Ensure previous dataserver authentication was removed
            ds_utils = self.get_authentication_utils(ds_folder)
            assert_that(ds_utils, has_length(0))
            assert_that(ds_sm.get('default', {}).get('authentication'),
                        is_(none()))

            # Ensure site util was added
            base_utils = self.get_authentication_utils(test_base_site)
            assert_that(base_utils, has_length(1))
            assert_that(test_base_sm.get('default', {}).get('authentication'),
                        not_(none()))

            child_utils = self.get_authentication_utils(test_child_site)
            assert_that(child_utils, has_length(1))
            assert_that(child_utils, not_(same_instance(base_utils[0])))
            assert_that(test_child_sm.get('default', {}).get('authentication'),
                        not_(none()))

    @mock_dataserver.WithMockDS
    def test_do_evolve_with_ds_util(self):
        self._test_evolve(add_ds_util=True)

    @mock_dataserver.WithMockDS
    def test_do_evolve_no_ds_util(self):
        self._test_evolve(add_ds_util=False)
