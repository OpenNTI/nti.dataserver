#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import has_item
from hamcrest import has_length
from hamcrest import assert_that

from nti.dataserver.users.communities import Community

from nti.dataserver.users.users import User

from nti.dataserver.utils import nti_join_community as nti_join

from nti.dataserver.tests import mock_dataserver

from nti.testing.base import ConfiguringTestBase


class TestNTIFollowEntities(ConfiguringTestBase):

    set_up_packages = ('nti.dataserver',)

    def _create_user(self, username=u'nt@nti.com', password=u'temp001'):
        ds = mock_dataserver.current_mock_ds
        usr = User.create_user(ds, username=username, password=password)
        return usr

    def _create_comm(self, username=u'comm@nti.com'):
        ds = mock_dataserver.current_mock_ds
        comm = Community.create_community(ds, username=username)
        return comm

    @mock_dataserver.WithMockDSTrans
    def test_join_follow(self):
        user = self._create_user()
        comms = []
        for x in range(1, 6):
            name = u'%s_comm@nti.com' % x
            comms.append(name)
            self._create_comm(name)

        not_found = nti_join.join_communities(user, comms, follow=True, 
                                              exitOnError=False)
        assert_that(not_found, has_length(0))
        followed = {e.username for e in user.entities_followed}
        membership = set(user.usernames_of_dynamic_memberships)
        assert_that(membership, has_length(6))
        for n in comms:
            assert_that(membership, has_item(n))
            assert_that(followed, has_item(n))
