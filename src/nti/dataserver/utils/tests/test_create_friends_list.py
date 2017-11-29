#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import has_length
from hamcrest import assert_that

from nti.dataserver.interfaces import IDynamicSharingTarget

from nti.dataserver.users.interfaces import IFriendlyNamed

from nti.dataserver.users.users import User

from nti.dataserver.utils import nti_create_friendslist as nti_cfl

from nti.dataserver.tests import mock_dataserver

from nti.testing.base import ConfiguringTestBase


class TestCreateFriendsLists(ConfiguringTestBase):

    set_up_packages = ('nti.dataserver',)

    def _create_user(self, username=u'nt@nti.com', password=u'temp001'):
        ds = mock_dataserver.current_mock_ds
        usr = User.create_user(ds, username=username, password=password)
        return usr

    @mock_dataserver.WithMockDSTrans
    def test_simple_friendslist(self):
        owner = self._create_user()
        friends = []
        for x in range(1, 5):
            username = u'friend%s@nti.com' % x
            friends.append(username)
            self._create_user(username)

        fl = nti_cfl.create_friends_list(owner, u'fl@nti.com',
                                         u'myfriends', friends, dynamic=False)
        current_friends = {x for x in fl}
        assert_that(current_friends, has_length(4))
        assert_that(IDynamicSharingTarget.providedBy(fl),
                    is_(False))
        assert_that(IFriendlyNamed(
            fl).realname, is_('myfriends'))

    @mock_dataserver.WithMockDSTrans
    def test_simple_dfl(self):
        owner = self._create_user()
        friends = []
        for x in range(1, 10):
            username = u'friend%s@nti.com' % x
            friends.append(username)
            self._create_user(username)

        fl = nti_cfl.create_friends_list(owner, u'fl@nti.com', u'dlfriends',
                                         friends, dynamic=True)
        current_friends = {x for x in fl}

        assert_that(current_friends, has_length(9))

        assert_that(IDynamicSharingTarget.providedBy(fl),
                    is_(True))

        assert_that(IFriendlyNamed(fl).realname,
                    is_('dlfriends'))
