#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import unittest

from hamcrest import assert_that
from hamcrest import has_length
from hamcrest import is_
from hamcrest import none

from pyramid.request import Request

from z3c.baseregistry.baseregistry import BaseComponents

from zope.authentication.interfaces import IAuthentication

from zope.component import globalSiteManager as BASE

from zope.interface.interfaces import IComponents

from zope.site.interfaces import INewLocalSite

from nti.app.authentication.subscribers import _decode_username_request
from nti.app.authentication.subscribers import install_site_authentication

from nti.appserver.policies.sites import BASEADULT

from nti.dataserver.tests import mock_dataserver

from nti.dataserver.tests.mock_dataserver import mock_db_trans

from nti.site.hostpolicy import synchronize_host_policies

from nti.site.interfaces import IHostPolicySiteManager

from nti.site.site import get_site_for_site_names

TEST_SITE = BaseComponents(BASEADULT,
                           name='test.nextthought.com',
                           bases=(BASEADULT,))


class TestDecode(unittest.TestCase):

    def test_decode_bad_auth(self):
        req = Request.blank('/')

        # blank password
        req.authorization = ('Basic', 'username:'.encode('base64'))

        username, password = _decode_username_request(req)

        assert_that(username, is_('username'))
        assert_that(password, is_(''))

        # malformed header
        req.authorization = ('Basic', 'username'.encode('base64'))

        username, password = _decode_username_request(req)

        assert_that(username, is_(none()))
        assert_that(password, is_(none()))

        # blank username
        req.authorization = ('Basic', ':foo'.encode('base64'))
        username, password = _decode_username_request(req)

        assert_that(username, is_(''))
        assert_that(password, is_('foo'))


class TestOnSiteCreation(mock_dataserver.DataserverLayerTest):

    def setUp(self):
        super(TestOnSiteCreation, self).setUp()
        site = TEST_SITE
        site.__init__(site.__parent__, name=site.__name__, bases=site.__bases__)
        BASE.registerUtility(site, name=site.__name__, provided=IComponents)
        BASE.registerHandler(install_site_authentication, required=(IHostPolicySiteManager, INewLocalSite))

    def tearDown(self):
        site = TEST_SITE
        BASE.unregisterUtility(site, name=site.__name__, provided=IComponents)
        super(TestOnSiteCreation, self).tearDown()

    def get_authentication_utils(self, site):
        sm = site.getSiteManager()
        authentication_utils = [reg for reg in sm.registeredUtilities()
                                if (reg.provided.isOrExtends(IAuthentication)
                                    and reg.name == '')]
        return authentication_utils

    @mock_dataserver.WithMockDS
    def test_add_auth_util(self):

        with mock_db_trans(self.ds) as conn:
            synchronize_host_policies()

            # Ensure util was added
            test_site = get_site_for_site_names(('test.nextthought.com',))
            base_utils = self.get_authentication_utils(test_site)
            assert_that(base_utils, has_length(1))

