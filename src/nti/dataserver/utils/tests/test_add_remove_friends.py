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

from nti.dataserver.users.friends_lists import FriendsList

from nti.dataserver.users.interfaces import IFriendlyNamed

from nti.dataserver.users.users import User

from nti.dataserver.utils import nti_add_remove_friends as nti_arf

from nti.dataserver.tests import mock_dataserver

from nti.testing.base import ConfiguringTestBase


class MockArgs(object):

    def __init__(self):
        self.owner = None
        self.name = None
        self.verbose = False
        self.add_members = ()
        self.remove_members = ()


class TestAddRemoveFriends(ConfiguringTestBase):

    set_up_packages = ('nti.dataserver',)

    def _create_user(self, username=u'nt@nti.com', password=u'temp001'):
        ds = mock_dataserver.current_mock_ds
        usr = User.create_user(ds, username=username, password=password)
        return usr

    def create_fl(self, owner, username=u'fl@nti.com', name=u'myfriends', members=()):
        fl = FriendsList(username=username)
        fl.creator = owner
        IFriendlyNamed(fl).realname = unicode(name)
        for member in members or ():
            fl.addFriend(member)
        owner.addContainedObject(fl)
        return fl

    @mock_dataserver.WithMockDSTrans
    def test_simple_add(self):
        owner = self._create_user()
        friend = self._create_user(u'friend@nti.com')
        friend2 = self._create_user(u'friend2@nti.com')
        fl = self.create_fl(owner, members=(friend,))
        current_friends = {x for x in fl}
        assert_that(current_friends, has_length(1))
        fl = nti_arf.add_remove_friends(owner, u'myfriends',
                                        (u'friend2@nti.com',))
        current_friends = {x for x in fl}
        assert_that(current_friends, has_item(friend))
        assert_that(current_friends, has_item(friend2))

    @mock_dataserver.WithMockDSTrans
    def test_simple_remove(self):
        owner = self._create_user()
        friend = self._create_user(u'friend@nti.com')
        friend2 = self._create_user(u'friend2@nti.com')
        fl = self.create_fl(owner, members=(friend, friend2))
        current_friends = {x for x in fl}
        assert_that(current_friends, has_length(2))
        fl = nti_arf.add_remove_friends(owner, u'myfriends',
                                        remove_members=(u'friend@nti.com',))
        current_friends = {x for x in fl}
        assert_that(current_friends, has_item(friend2))
        assert_that(current_friends, not has_item(friend))

    @mock_dataserver.WithMockDSTrans
    def test_args(self):
        owner = self._create_user()
        friend = self._create_user(u'friend@nti.com')
        friend2 = self._create_user(u'friend2@nti.com')
        self.create_fl(owner)
        args = MockArgs()
        args.owner = u'nt@nti.com'
        args.name = u'fl@nti.com'
        args.add_members = (u'friend@nti.com', u'friend2@nti.com')
        fl = nti_arf.process_params(args)
        current_friends = {x for x in fl}
        assert_that(current_friends, has_item(friend2))
        assert_that(current_friends, has_item(friend))
