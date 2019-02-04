#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import

from hamcrest import assert_that
from hamcrest import has_entry
from hamcrest import has_item
from hamcrest import is_not
does_not = is_not

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.dataserver.tests import mock_dataserver

__docformat__ = "restructuredtext en"


# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

class TestUserPolicies(ApplicationLayerTest):

    @WithSharedApplicationMockDS(users=True, testapp=True)
    def test_can_manage_owned_groups_capability(self):
        # test admin has capability
        res = self.testapp.get('/dataserver2',
                               status=200)
        assert_that(res.json_body, has_entry('CapabilityList',
                                             has_item('nti.platform.groups.can_manage_owned_groups')))

        # test regular user does not
        with mock_dataserver.mock_db_trans(self.ds):
            self._create_user('regular_dude')

        regular_env = self._make_extra_environ(user='regular_dude')
        res = self.testapp.get('/dataserver2',
                               extra_environ=regular_env,
                               status=200)
        assert_that(res.json_body, does_not(has_entry('CapabilityList',
                                                      has_item('nti.platform.groups.can_manage_owned_groups'))))
