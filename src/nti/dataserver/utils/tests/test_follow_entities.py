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

from nti.dataserver.utils import nti_follow_entity as nti_follow

from nti.dataserver.tests import mock_dataserver

from nti.testing.base import ConfiguringTestBase


class TestNTIFollowEntities(ConfiguringTestBase):

    set_up_packages = ('nti.dataserver',)

    def _create_user(self, username=u'nt@nti.com', password='utemp001'):
        ds = mock_dataserver.current_mock_ds
        usr = User.create_user(ds, username=username, password=password)
        return usr

    def _create_comm(self, username=u'comm@nti.com'):
        ds = mock_dataserver.current_mock_ds
        comm = Community.create_community(ds, username=username)
        return comm

    @mock_dataserver.WithMockDSTrans
    def test_simple_follow(self):
        user = self._create_user()
        follow = []
        for x in range(1, 3):
            name = u'%s_comm@nti.com' % x
            follow.append(name)
            self._create_comm(name)

        found, not_found, member_of = nti_follow.follow_entities(user, follow)
        assert_that(found, has_length(2))
        assert_that(not_found, has_length(0))
        assert_that(member_of, has_length(2))

        s = set(user.usernames_of_dynamic_memberships)
        assert_that(s, has_length(3))
        for n in follow:
            assert_that(s, has_item(n))

    @mock_dataserver.WithMockDSTrans
    def test_follow_user(self):
        user = self._create_user()
        follow = []
        for x in range(1, 3):
            name = u'user%s' % x
            follow.append(name)
            user = self._create_user(name)

        found, not_found, member_of = nti_follow.follow_entities(user, follow)
        assert_that(found, has_length(2))
        assert_that(not_found, has_length(0))
        assert_that(member_of, has_length(0))

        s = set(user.following)
        assert_that(s, has_length(2))
        for n in follow:
            assert_that(s, has_item(n))
