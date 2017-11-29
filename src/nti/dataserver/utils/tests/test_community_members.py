#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import has_length
from hamcrest import assert_that

from nti.dataserver.users.users import User

from nti.dataserver.users.communities import Community

from nti.dataserver.utils.nti_community_members import get_member_info

from nti.dataserver.tests import mock_dataserver

from nti.testing.base import ConfiguringTestBase


class TestCommunityMembers(ConfiguringTestBase):

    set_up_packages = ('nti.dataserver',)

    def _create_user(self, username='nt@nti.com', password='temp001'):
        ds = mock_dataserver.current_mock_ds
        usr = User.create_user(ds, username=username, password=password)
        return usr

    def _create_comm(self, username='comm@nti.com'):
        ds = mock_dataserver.current_mock_ds
        comm = Community.create_community(ds, username=username)
        return comm

    @mock_dataserver.WithMockDSTrans
    def test_get_member_info(self):
        comm = self._create_comm()
        for x in range(0, 5):
            name = u'%s_user@nti.com' % x
            user = self._create_user(name)
            user.record_dynamic_membership(comm)
            user.follow(comm)

        members = list(get_member_info(comm))
        assert_that(members, has_length(5))
        for member in members:
            assert_that(member, has_length(4))
