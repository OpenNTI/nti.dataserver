#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import has_entry
from hamcrest import assert_that

import json

from zope.annotation import IAnnotations

from nti.appserver import logon

from nti.appserver.link_providers import link_provider

from nti.containers.dicts import LastModifiedDict

from nti.dataserver import users

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.app.testing.webtest import TestApp

from nti.dataserver.tests import mock_dataserver


class TestLinkProviderAdminViews(ApplicationLayerTest):

    def _test_reset(self, view_name, link_name):
        with mock_dataserver.mock_db_trans(self.ds):
            user = self._create_user()
            annot = IAnnotations(user)
            link_dict = annot.get(link_provider._GENERATION_LINK_KEY)
            if link_dict is None:
                link_dict = LastModifiedDict()
                link_dict[link_name] = u'20130501'
                annot[link_provider._GENERATION_LINK_KEY] = link_dict

        testapp = TestApp(self.app)
        testapp.post('/dataserver2/%s' % view_name,
                     json.dumps({'username': 'sjohnson@nextthought.com'}),
                     extra_environ=self._make_extra_environ(),
                     status=204)

        with mock_dataserver.mock_db_trans(self.ds):
            user = users.User.get_user('sjohnson@nextthought.com')
            annot = IAnnotations(user)
            link_dict = annot.get(link_provider._GENERATION_LINK_KEY)
            assert_that(link_dict, has_entry(link_name, ''))

    @WithSharedApplicationMockDS
    def test_reset_initial_tos_page(self):
        self._test_reset('@@reset_initial_tos_page',
                         logon.REL_INITIAL_TOS_PAGE)

    @WithSharedApplicationMockDS
    def test_reset_welcome_page(self):
        self._test_reset('@@reset_welcome_page',
                         logon.REL_INITIAL_WELCOME_PAGE)
