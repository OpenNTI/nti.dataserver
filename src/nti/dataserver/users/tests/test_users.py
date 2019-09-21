#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import is_in
from hamcrest import is_not
from hamcrest import not_none
from hamcrest import contains
from hamcrest import has_item
from hamcrest import has_entry
from hamcrest import has_value
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_property
from hamcrest import greater_than
from hamcrest import greater_than_or_equal_to
does_not = is_not

from nose.tools import assert_raises

from nti.testing.matchers import is_false
from nti.testing.matchers import provides
from nti.testing.matchers import verifiably_provides

from nti.testing.time import time_monotonically_increases

import fudge

import copy
import time
import unittest

from zope import component

from zope.component import eventtesting

from zope.container.interfaces import InvalidItemType

from zope.location.interfaces import ISublocations

from zc.intid.interfaces import IIntIds

from z3c.password.interfaces import InvalidPassword

import persistent.wref

from nti.contentrange.contentrange import ContentRangeDescription

from nti.coremetadata.mixins import ZContainedMixin as ContainedMixin

from nti.dataserver.activitystream_change import Change

from nti.dataserver.contenttypes import Note

from nti.dataserver.interfaces import SC_DELETED
from nti.dataserver.interfaces import SC_CREATED
from nti.dataserver.interfaces import SC_MODIFIED
from nti.dataserver.interfaces import SYSTEM_USER_ID
from nti.dataserver.interfaces import SYSTEM_USER_NAME

from nti.dataserver.interfaces import IFriendsList
from nti.dataserver.interfaces import IIntIdIterable
from nti.dataserver.interfaces import IEntityContainer
from nti.dataserver.interfaces import IDynamicSharingTarget
from nti.dataserver.interfaces import ITargetedStreamChangeEvent
from nti.dataserver.interfaces import ILengthEnumerableEntityContainer

from nti.dataserver.users.black_list import UserBlacklistedStorage

from nti.dataserver.users.communities import Everyone
from nti.dataserver.users.communities import Community

from nti.dataserver.users.device import Device

from nti.dataserver.users.entity import Entity

from nti.dataserver.users.friends_lists import FriendsList
from nti.dataserver.users.friends_lists import DynamicFriendsList

from nti.dataserver.users.users import User

from nti.dataserver.users.users import _FriendsListMap as FriendsListContainer

from nti.externalization.externalization import to_external_object

from nti.externalization.internalization import update_from_external_object

from nti.externalization.persistence import getPersistentState

from nti.ntiids.ntiids import find_object_with_ntiid

from nti.ntiids.oids import to_external_ntiid_oid

from nti.dataserver.tests import mock_dataserver

from nti.dataserver.tests.mock_dataserver import WithMockDS
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans
from nti.dataserver.tests.mock_dataserver import DataserverLayerTest


class PersistentContainedThreadable(ContainedMixin, persistent.Persistent):

    creator = None
    lastModified = 0
    inReplyTo = None
    references = ()
    shared_with = True

    def isSharedDirectlyWith(self, *unused_args):
        return self.shared_with

    def __repr__(self):
        return repr((self.__class__.__name__, self.containerId, self.id))


class TestMisc(unittest.TestCase):

    def test_create_friends_list_through_registry(self):
        def _test(name, dynamic_sharing=False):
            user = User(u'foo12')
            created = user.maybeCreateContainedObjectWithType(
                name,
                {'Username': u'Friend', 'IsDynamicSharing': dynamic_sharing}
            )
            assert_that(created, is_(FriendsList))
            assert_that(created.username, is_('Friend'))
            assert_that(created, provides(IFriendsList))

            if dynamic_sharing:
                assert_that(created,
                            verifiably_provides(IDynamicSharingTarget))
            else:
                assert_that(created,
                            does_not(provides(IDynamicSharingTarget)))

        _test('FriendsLists')
        # case insensitive
        _test('friendslists')
        # can create dynamic
        _test('Friendslists', True)

    def test_adding_wrong_type_to_friendslist(self):
        friends = FriendsListContainer()
        with assert_raises(InvalidItemType):
            friends['k'] = 'v'

    def test_friends_list_case_insensitive(self):
        user = User(u'foo@bar')
        fl = user.maybeCreateContainedObjectWithType(
            'FriendsLists', {'Username': u'Friend'}
        )
        user.addContainedObject(fl)

        assert_that(user.getContainedObject("FriendsLists", "Friend"),
                    is_(user.getContainedObject('FriendsLists', "friend")))

    def test_everyone_has_creator(self):
        assert_that(Everyone(),
                    has_property('creator', SYSTEM_USER_NAME))

    def test_cannot_create_with_invalid_name(self):
        with assert_raises(zope.schema.interfaces.ConstraintNotSatisfied):
            Entity(username=SYSTEM_USER_NAME)

        with assert_raises(zope.schema.interfaces.ConstraintNotSatisfied):
            Entity(username=SYSTEM_USER_ID)

    def test_user_blacklisted_storage(self):
        storage = UserBlacklistedStorage()
        storage.add('ichigo')
        assert_that(storage, has_length(1))
        assert_that('ichigo', is_in(storage))
        storage.blacklist_user('aizen')
        assert_that(storage, has_length(2))
        storage.remove_blacklist_for_user('ichigo')
        assert_that(storage, has_length(1))
        storage.clear()
        assert_that(storage, has_length(0))


class TestUser(DataserverLayerTest):

    layer = mock_dataserver.SharedConfiguringTestLayer

    @WithMockDSTrans
    def test_type_error(self):

        with assert_raises(TypeError):
            Entity.get_entity(username={})

        with assert_raises(TypeError):
            Entity.get_entity(username=1)

    @WithMockDSTrans
    def test_can_find_friendslist_with_ntiid(self):

        user1 = User.create_user(self.ds, username=u'foo@bar')
        user2 = User.create_user(self.ds, username=u'foo2@bar')

        fl1 = user1.maybeCreateContainedObjectWithType(
            'FriendsLists', {'Username': u'Friend'}
        )
        user1.addContainedObject(fl1)

        fl2 = user2.maybeCreateContainedObjectWithType(
            'FriendsLists', {'Username': u'Friend'}
        )
        user2.addContainedObject(fl2)

        assert_that(fl1.NTIID, is_not(fl2.NTIID))

        assert_that(user1.get_entity(fl2.NTIID), is_(fl2))
        assert_that(user2.get_entity(fl1.NTIID), is_(fl1))
        assert_that(User.get_entity(fl1.NTIID), is_(fl1))
        assert_that(User.get_entity('foo@bar'), is_(user1))

    @WithMockDSTrans
    def test_friendslist_updated_through_user_updates_last_mod(self):
        user = User.create_user(self.ds,  username=u'foo@bar')
        friend = User.create_user(self.ds, username=u'friend@bar')
        fl = user.maybeCreateContainedObjectWithType(
            'FriendsLists', {'Username': u'Friend'}
        )
        user.addContainedObject(fl)
        fl.lastModified = 0
        now = time.time()

        with user.updates():
            fl2 = user.getContainedObject(fl.containerId, fl.id)
            update_from_external_object(fl2, {'friends': [friend.username]})

        assert_that(fl.lastModified, is_(greater_than_or_equal_to(now)))
        assert_that(user.getContainer(fl.containerId).lastModified,
                    is_(greater_than_or_equal_to(now)))

    def test_create_device_through_registry(self):
        user = User(u'foo@bar', u'temp')

        created = user.maybeCreateContainedObjectWithType(
            'Devices', u'deadbeef'
        )
        assert_that(created, is_(Device))
        assert_that(created.id, is_('deadbeef'))
        assert_that(created.deviceId, is_('deadbeef'.decode('hex')))
        assert_that(created.containerId, is_('Devices'))
        assert_that(to_external_object(created),
                    has_entry('ID', 'deadbeef'))
        assert_that(created, is_(created))

        user.addContainedObject(created)
        assert_that(user.getContainedObject(created.containerId, created.id),
                    is_(created))

    def test_clear_notification_count(self):
        user = User(u'foo@bar', u'temp')
        user.lastLoginTime = 1
        user.notificationCount.set(5)

        update_from_external_object(user, {'lastLoginTime': 2})
        assert_that(user.lastLoginTime, is_(2))
        assert_that(user.notificationCount, has_property('value', 0))

        user = User(u'foo@bar', u'temp')
        user.lastLoginTime = 1
        user.notificationCount.value = 5
        update_from_external_object(user, {'NotificationCount': 2})
        assert_that(user.lastLoginTime, is_(1))
        assert_that(user.notificationCount, has_property('value', 2))

    @WithMockDS
    def test_creating_friendslist_goes_to_stream(self):
        with mock_dataserver.mock_db_trans(self.ds):
            user = User.create_user(self.ds, username=u'foo@bar')
            user2 = User.create_user(self.ds, username=u'friend@bar')
            with user.updates():
                fl = user.maybeCreateContainedObjectWithType(
                    'FriendsLists', {'Username': u'Friends'}
                )
                user.addContainedObject(fl)
                update_from_external_object(fl, {'friends':  [u'friend@bar']})

            user2_stream = user2.getContainedStream('')
            assert_that(user2_stream, has_length(1))

    @WithMockDSTrans
    def test_cannot_create_twice(self):
        user1 = User.create_user(self.ds, username=u'foo@bar',
                                 password=u'temp001')
        with assert_raises(KeyError):
            User.create_user(self.ds, username=user1.username,
                             password=u'temp001')

    @WithMockDSTrans
    def test_cannot_reset_password_if_not_match(self):
        user1 = User.create_user(self.ds, username=u'foo@bar',
                                 password=u'temp001')
        with assert_raises(InvalidPassword):
            user1.updateFromExternalObject({'password': u'temp003'})
        with assert_raises(InvalidPassword):
            user1.updateFromExternalObject(
                {'password': u'temp003', 'old_password': u'temp002'}
            )

    @WithMockDSTrans
    def test_cannot_have_whitespace_pwd(self):
        with assert_raises(InvalidPassword):
            User.create_user(self.ds, username=u"foo@bar", password=u' \t ')

    @WithMockDSTrans
    def test_share_unshare_note(self):
        user1 = User.create_user(self.ds, username=u'foo@bar',
                                 password=u'temp001')
        user2 = User.create_user(self.ds, username=u'fab@bar',
                                 password=u'temp001')

        note = Note()
        note.body = [u'text']
        note.containerId = u'c1'
        note.creator = user1.username

        user1.addContainedObject(note)
        assert_that(note.id, is_not(none()))

        note.addSharingTarget(user2)
        note.id = u'foobar'  # to ensure it doesn't get used or changed by the sharing process
        user2._noticeChange(Change(Change.SHARED, note))
        assert_that(note.id, is_('foobar'))
        assert_that(note, is_in(user2.getSharedContainer('c1')))

        user2._noticeChange(Change(Change.DELETED, note))
        assert_that(persistent.wref.WeakRef(note),
                    is_not(is_in(user2.getSharedContainer('c1'))))
        assert_that(note.id, is_('foobar'))

    @WithMockDS
    @fudge.patch('nti.dataserver.activitystream.hasQueryInteraction')
    def test_share_unshare_note_with_dynamic_friendslist(self, mock_hqi):
        mock_hqi.is_callable().with_args().returns(True)
        with mock_dataserver.mock_db_trans(self.ds):
            user1 = User.create_user(self.ds, username=u'foo@bar',
                                     password=u'temp001')
            user2 = User.create_user(self.ds, username=u'fab@bar',
                                     password=u'temp001')

            friends_list = DynamicFriendsList(username=u'Friends')
            friends_list.creator = user1
            user1.addContainedObject(friends_list)
            friends_list.addFriend(user2)

            note = Note()
            note.body = [u'text']
            note.containerId = u'c1'
            note.creator = user1.username

            with user1.updates():
                note.addSharingTarget(friends_list)
                user1.addContainedObject(note)

            assert_that(note.id, is_not(none()))

            assert_that(note, is_in(user2.getSharedContainer('c1')))
            assert_that(friends_list, is_in(note.sharingTargets))
            assert_that(user2.getSharedContainer('c1'), has_length(1))

            with user1.updates():
                user1.deleteContainedObject(note.containerId, note.id)

            assert_that(note, is_not(is_in(user2.getSharedContainer('c1'))))
            assert_that(user2.getSharedContainer('c1'), has_length(0))

    @WithMockDS
    @fudge.patch('nti.dataserver.activitystream.hasQueryInteraction')
    def test_share_unshare_note_with_friendslist(self, mock_hqi):
        mock_hqi.is_callable().with_args().returns(True)
        with mock_dataserver.mock_db_trans(self.ds):
            user1 = User.create_user(self.ds, username=u'foo@bar',
                                     password=u'temp001')
            user2 = User.create_user(self.ds, username=u'fab@bar',
                                     password=u'temp001')

            friends_list = FriendsList(username=u'Friends')
            friends_list.creator = user1
            user1.addContainedObject(friends_list)
            friends_list.addFriend(user2)

            note = Note()
            note.body = [u'text']
            note.containerId = u'c1'
            note.creator = user1.username

            with user1.updates():
                note.addSharingTarget(friends_list)
                user1.addContainedObject(note)
            assert_that(note.id, is_not(none()))

            assert_that(note, is_in(user2.getSharedContainer('c1')))
            assert_that(user2, is_in(note.sharingTargets))

            with user1.updates():
                user1.deleteContainedObject(note.containerId, note.id)

            assert_that(note, is_not(is_in(user2.getSharedContainer('c1'))))

    @WithMockDS
    @fudge.patch('nti.dataserver.activitystream.hasQueryInteraction')
    def test_share_note_directly_and_indirectly_with_dfl_unshare_with_dfl(self, mock_hqi):
        mock_hqi.is_callable().with_args().returns(True)
        with mock_dataserver.mock_db_trans(self.ds):
            user1 = User.create_user(self.ds, username=u'foo@bar',
                                     password=u'temp001')
            user2 = User.create_user(self.ds, username=u'fab@bar',
                                     password=u'temp001')

            friends_list = DynamicFriendsList(username=u'Friends')
            friends_list.creator = user1
            user1.addContainedObject(friends_list)
            friends_list.addFriend(user2)

            note = Note()
            note.body = [u'text']
            note.containerId = u'c1'
            note.creator = user1.username
            user2.notificationCount.value = 0
            with user1.updates():
                note.addSharingTarget(friends_list)  # indirect sharing
                note.addSharingTarget(user2)  # direct sharing
                user1.addContainedObject(note)
            assert_that(note.id, is_not(none()))

            assert_that(note, is_in(user2.getSharedContainer('c1')))
            assert_that(user2, is_in(note.sharingTargets))
            assert_that(user2.notificationCount,
                        has_property('value', 1))  # original

            with user1.updates():
                note = user1.getContainedObject('c1', note.id)
                # Now, only directly shared
                note.updateSharingTargets((user2,), notify=True)

            # Nothing changed for the recipient
            assert_that(note, is_in(user2.getSharedContainer('c1')))
            assert_that(user2, is_in(note.sharingTargets))
            assert_that(user2.notificationCount, has_property('value', 1))

    @WithMockDS
    @fudge.patch('nti.dataserver.activitystream.hasQueryInteraction')
    def test_share_note_directly_and_indirectly_with_community_unshare_with_community(self, mock_hqi):
        """
        An item shared both directly and indirectly with me is
        still shared with me if the indirect sharing is removed.
        """
        mock_hqi.is_callable().with_args().returns(True)
        with mock_dataserver.mock_db_trans(self.ds):
            user1 = User.create_user(self.ds, username=u'foo@bar',
                                     password=u'temp001')
            user2 = User.create_user(self.ds, username=u'fab@bar',
                                     password=u'temp001')
            community = Community.create_entity(self.ds,
                                                username=u'TheCommunity')

            user1.record_dynamic_membership(community)
            user2.record_dynamic_membership(community)
            user2.follow(user1)

            note = Note()
            note.body = [u'text']
            note.containerId = u'c1'
            note.creator = user1.username
            user2.notificationCount.value = 0
            with user1.updates():
                note.addSharingTarget(community)  # indirect sharing
                note.addSharingTarget(user2)  # direct sharing
                user1.addContainedObject(note)
            assert_that(note.id, is_not(none()))

            assert_that(note, is_in(user2.getSharedContainer('c1')))
            assert_that(user2, is_in(note.sharingTargets))
            assert_that(user2.notificationCount,
                        has_property('value', 1))  # original

            with user1.updates():
                note = user1.getContainedObject('c1', note.id)
                # Now, only directly shared
                note.updateSharingTargets((user2,), notify=True)

            # Nothing changed for the recipient
            assert_that(note, is_in(user2.getSharedContainer('c1')))
            assert_that(user2, is_in(note.sharingTargets))
            assert_that(user2.notificationCount, has_property('value', 1))
            stream = user2.getContainedStream('c1')
            __traceback_info__ = stream
            assert_that(stream, has_length(1))
            assert_that(stream[0],
                        has_property('type', SC_MODIFIED))

    @WithMockDS
    @fudge.patch('nti.dataserver.activitystream.hasQueryInteraction')
    def test_share_note_directly_and_indirectly_with_dfl_unshare_directly(self, mock_hqi):
        mock_hqi.is_callable().with_args().returns(True)
        with mock_dataserver.mock_db_trans(self.ds):
            user1 = User.create_user(self.ds, username=u'foo@bar',
                                     password=u'temp001')
            user2 = User.create_user(self.ds, username=u'fab@bar',
                                     password=u'temp001')

            friends_list = DynamicFriendsList(username='uFriends')
            friends_list.creator = user1
            user1.addContainedObject(friends_list)
            friends_list.addFriend(user2)

            note = Note()
            note.body = [u'text']
            note.containerId = u'c1'
            note.creator = user1.username
            user2.notificationCount.value = 0
            with user1.updates():
                note.addSharingTarget(friends_list)  # indirect sharing
                note.addSharingTarget(user2)  # direct sharing
                user1.addContainedObject(note)
            assert_that(note.id, is_not(none()))

            assert_that(note, is_in(user2.getSharedContainer('c1')))
            assert_that(user2, is_in(note.sharingTargets))
            assert_that(user2.notificationCount,
                        has_property('value', 1))  # original
            stream = user2.getContainedStream('c1')
            assert_that(stream, has_length(1))
            assert_that(stream[0],
                        has_property('type', SC_CREATED))

            with user1.updates():
                note = user1.getContainedObject('c1', note.id)
                # Now, only indirectly shared
                note.updateSharingTargets((friends_list,), notify=True)

            # Nothing changed for the recipient
            assert_that(note, is_in(user2.getSharedContainer('c1')))
            assert_that(user2.notificationCount, has_property('value', 1))
            stream = user2.getContainedStream('c1')
            assert_that(stream, has_length(1))
            assert_that(stream[0],
                        has_property('type', SC_MODIFIED))

    @WithMockDS
    @fudge.patch('nti.dataserver.activitystream.hasQueryInteraction')
    def test_share_note_directly_and_indirectly_with_community_unshare_directly(self, mock_hqi):
        mock_hqi.is_callable().with_args().returns(True)
        with mock_dataserver.mock_db_trans(self.ds):
            user1 = User.create_user(self.ds, username=u'foo@bar',
                                     password=u'temp001')
            user2 = User.create_user(self.ds, username=u'fab@bar',
                                     password=u'temp001')
            community = Community.create_entity(self.ds,
                                                username=u'TheCommunity')

            user1.record_dynamic_membership(community)
            user2.record_dynamic_membership(community)
            user2.follow(user1)
            user2_changes = list()

            def _noticeChange(change):
                user2_changes.append(copy.copy(change))
                User._noticeChange(user2, change)
            user2._noticeChange = _noticeChange
            try:
                note = Note()
                note.body = [u'text']
                note.containerId = u'c1'
                note.creator = user1.username
                user2.notificationCount.value = 0
                with user1.updates():
                    note.addSharingTarget(community)  # indirect sharing
                    note.addSharingTarget(user2)  # direct sharing
                    user1.addContainedObject(note)
                assert_that(note.id, is_not(none()))

                assert_that(note, is_in(user2.getSharedContainer('c1')))
                assert_that(user2, is_in(note.sharingTargets))
                assert_that(user2.notificationCount,
                            has_property('value', 1))  # original
                stream = user2.getContainedStream('c1')
                assert_that(stream, has_length(1))
                assert_that(stream[0],
                            has_property('type', SC_CREATED))

                with user1.updates():
                    note = user1.getContainedObject('c1', note.id)
                    # Now, only indirectly shared
                    note.updateSharingTargets((community,), notify=True)

                # Nothing changed for the recipient, they just got a modified
                # event
                assert_that(note, is_in(user2.getSharedContainer('c1')))
                assert_that(user2.notificationCount, has_property('value', 1))
                stream = user2.getContainedStream('c1')
                assert_that(stream, has_length(1))
                assert_that(stream[0],
                            has_property('type', SC_MODIFIED))

                assert_that(user2_changes, has_length(2))
                assert_that(user2_changes[0],
                            has_property('type', SC_CREATED))
                assert_that(user2_changes[1],
                            has_property('type', SC_DELETED))
                assert_that(user2_changes[1],
                            has_property('send_change_notice', is_false()))

                # Now at this point, deleting the object really does remove it
                with user1.updates():
                    user1.deleteContainedObject(note.containerId, note.id)

                assert_that(note,
                            is_not(is_in(user2.getSharedContainer('c1'))))
                stream = user2.getContainedStream('c1')
                assert_that(stream, has_length(0))
            finally:
                # Must not try to commit this
                del user2._noticeChange

    @WithMockDS
    @fudge.patch('nti.dataserver.activitystream.hasQueryInteraction')
    def test_share_unshare_note_with_dynamic_friendslist_external(self, mock_hqi):
        mock_hqi.is_callable().with_args().returns(True)
        with mock_dataserver.mock_db_trans(self.ds):
            user1 = User.create_user(self.ds, username=u'foo@bar',
                                     password=u'temp001')
            user2 = User.create_user(self.ds, username=u'fab@bar',
                                     password=u'temp001')

            friends_list = DynamicFriendsList(username=u'Friends')
            friends_list.creator = user1
            user1.addContainedObject(friends_list)
            friends_list.addFriend(user2)

            note = Note()
            note.body = [u'text']
            note.containerId = u'c1'
            note.creator = user1.username
            note.applicableRange = ContentRangeDescription()
            user1.addContainedObject(note)

            with user1.updates():
                the_note = user1.getContainedObject(note.containerId, note.id)
                update_from_external_object(
                    the_note, {'sharedWith': [friends_list.NTIID]}
                )

            assert_that(note.id, is_not(none()))
            assert_that(note, is_in(user2.getSharedContainer('c1')))
            assert_that(friends_list, is_in(note.sharingTargets))

            with user1.updates():
                the_note = user1.getContainedObject(note.containerId, note.id)
                update_from_external_object(the_note, {'sharedWith': []})

            assert_that(note, is_not(is_in(user2.getSharedContainer('c1'))))

    @WithMockDS
    @fudge.patch('nti.dataserver.activitystream.hasQueryInteraction')
    def test_share_unshare_note_with_friendslist_external(self, mock_hqi):
        mock_hqi.is_callable().with_args().returns(True)
        with mock_dataserver.mock_db_trans(self.ds):
            user1 = User.create_user(self.ds, username=u'foo@bar',
                                     password=u'temp001')
            user2 = User.create_user(self.ds, username=u'fab@bar',
                                     password=u'temp001')

            friends_list = FriendsList(username=u'Friends')
            friends_list.creator = user1
            user1.addContainedObject(friends_list)
            friends_list.addFriend(user2)

            note = Note()
            note.body = [u'text']
            note.containerId = u'c1'
            note.creator = user1.username
            note.applicableRange = ContentRangeDescription()
            user1.addContainedObject(note)

            with user1.updates():
                the_note = user1.getContainedObject(note.containerId, note.id)
                update_from_external_object(
                    the_note, {'sharedWith': [friends_list.NTIID]}
                )

            assert_that(note.id, is_not(none()))
            assert_that(note, is_in(user2.getSharedContainer('c1')))
            assert_that(user2, is_in(note.sharingTargets))

            with user1.updates():
                the_note = user1.getContainedObject(note.containerId, note.id)
                update_from_external_object(the_note, {'sharedWith': []})

            assert_that(note, is_not(is_in(user2.getSharedContainer('c1'))))

    @mock_dataserver.WithMockDS
    @time_monotonically_increases
    @fudge.patch('nti.dataserver.activitystream.hasQueryInteraction')
    def test_share_note_with_updates(self, mock_hqi):
        mock_hqi.is_callable().with_args().returns(True)
        with mock_dataserver.mock_db_trans():
            user1 = User.create_user(mock_dataserver.current_mock_ds,
                                     username=u'foo@bar')
            User.create_user(mock_dataserver.current_mock_ds,
                             username=u'fab@bar')

            note = Note()
            note.body = [u'text']
            note.containerId = u'c1'
            note.creator = user1.username

            user1.addContainedObject(note)
            assert_that(note.id, is_not(none()))

        with mock_dataserver.mock_db_trans():
            user1 = User.get_user(u'foo@bar',
                                  dataserver=mock_dataserver.current_mock_ds)
            eventtesting.clearEvents()
            with user1.updates():
                c_note = user1.getContainedObject(note.containerId, note.id)
                c_note.updateSharingTargets(c_note.sharingTargets | set(
                    [User.get_user('fab@bar', dataserver=mock_dataserver.current_mock_ds)]),
                    notify=True)
                assert_that(list(c_note.flattenedSharingTargetNames),
                            is_(['fab@bar']))
                assert_that(getPersistentState(c_note),
                            is_(persistent.CHANGED))
                lm = c_note.lastModified

            assert_that(user1.containers['c1'].lastModified, is_(
                greater_than_or_equal_to(lm)))
            assert_that(user1.containers['c1'].lastModified, is_(
                greater_than_or_equal_to(user1.containers['c1'][note.id].lastModified)))

            evts = eventtesting.getEvents(ITargetedStreamChangeEvent)

            assert_that(evts, has_length(1))
            assert_that(evts[0].object, has_property('type', 'Shared'))
            assert_that(evts[0].object, has_property('object', c_note))

    @mock_dataserver.WithMockDS
    @fudge.patch('nti.dataserver.activitystream.hasQueryInteraction')
    def test_delete_shared_note_notifications(self, mock_hqi):
        mock_hqi.is_callable().with_args().returns(True)
        with mock_dataserver.mock_db_trans():
            user1 = User.create_user(mock_dataserver.current_mock_ds,
                                     username=u'foo@bar')
            user2 = User.create_user(mock_dataserver.current_mock_ds,
                                     username=u'fab@bar')

            note = Note()
            note.body = [u'text']
            note.containerId = u'c1'
            note.creator = user1.username

            user1.addContainedObject(note)
            assert_that(note.id, is_not(none()))

            note.addSharingTarget(user2)

        with mock_dataserver.mock_db_trans():
            nots = []
            user1 = User.get_user('foo@bar',
                                  dataserver=mock_dataserver.current_mock_ds)
            user1._postNotification = lambda *args: nots.append(args)
            eventtesting.clearEvents()

            with user1.updates():
                c_note = user1.getContainedObject(note.containerId, note.id)
                user1.deleteContainedObject(c_note.containerId, c_note.id)
                assert_that(getPersistentState(c_note),
                            is_(persistent.CHANGED))

            del user1._postNotification

            # No modified notices, just the Deleted notice.
            evts = eventtesting.getEvents(ITargetedStreamChangeEvent)

            assert_that(evts, has_length(1))
            assert_that(evts[0].object, has_property('type', 'Deleted'))
            assert_that(evts[0].object, has_property('object', c_note))

    @WithMockDSTrans
    def test_getSharedContainer_defaults(self):
        user = User.create_user(self.ds, username=u'sjohnson@nextthought.com',
                                password=u'temp001')
        assert_that(user.getSharedContainer('foo', 42), is_(42))

        c = PersistentContainedThreadable()
        c.containerId = u'foo'
        c.id = u'a'
        component.getUtility(IIntIds).register(c)

        user._addSharedObject(c)
        assert_that(user.getSharedContainer('foo'), has_length(1))

        # Deleting it, we get back the now-empty container, not the default
        # value
        user._removeSharedObject(c)
        assert_that(list(user.getSharedContainer('foo', 42)), has_length(0))

    @WithMockDSTrans
    def test_mute_conversation(self):
        user = User.create_user(self.ds, username=u'sjohnson@nextthought.com',
                                password=u'temp001')

        c = PersistentContainedThreadable()
        c.containerId = u'foo'
        c.id = u'a'
        c.creator = u'foo'
        self.ds.root._p_jar.add(c)
        component.getUtility(IIntIds).register(c)
        change = Change(Change.CREATED, c)
        change.creator = u'foo'
        user._acceptIncomingChange(change)
        assert_that(user.getSharedContainer('foo'), has_length(1))
        assert_that(user.getContainedStream('foo'), has_length(1))

        user.mute_conversation(to_external_ntiid_oid(c))

        # Now, the shared container is empty
        assert_that(list(user.getSharedContainer('foo', 42)), has_length(0))
        assert_that(user.getContainedStream('foo'), has_length(0))

        # Stays empty as we reply
        reply = PersistentContainedThreadable()
        reply.containerId = u'foo'
        reply.id = u'b'
        reply.inReplyTo = c
        self.ds.root._p_jar.add(reply)
        component.getUtility(IIntIds).register(reply)
        change = Change(Change.SHARED, reply)
        user._noticeChange(change)

        assert_that(list(user.getSharedContainer('foo', 42)), has_length(0))
        assert_that(user.getContainedStream('foo'), has_length(0))

        # Stays empty as we reference
        reference = PersistentContainedThreadable()
        reference.containerId = u'foo'
        reference.id = u'3'
        self.ds.root._p_jar.add(reference)
        reference.references = [c]

        component.getUtility(IIntIds).register(reference)
        change = Change(Change.SHARED, reference)
        user._noticeChange(change)

        assert_that(list(user.getSharedContainer('foo', 42)), has_length(0))
        assert_that(user.getContainedStream('foo'), has_length(0))

        # But unmuting it brings all the objects back
        user.unmute_conversation(to_external_ntiid_oid(c))
        assert_that(list(user.getSharedContainer('foo')), has_length(3))

        user.mute_conversation(to_external_ntiid_oid(c))
        # and they can all go away
        assert_that(list(user.getSharedContainer('foo', 42)), has_length(0))
        assert_that(user.getContainedStream('foo'), has_length(0))
        # If a DELETE arrives while muted, then it is still missing when
        # unmuted
        change = Change(Change.DELETED, reference)
        user._noticeChange(change)

        user.unmute_conversation(to_external_ntiid_oid(c))
        assert_that(user.getSharedContainer('foo'), has_length(2))

    @WithMockDSTrans
    def test_getContainedStream_Note_shared_community_cache(self):
        #"We should be able to get the contained stream if there are things shared with a community in the cache"
        user = User.create_user(self.ds, username=u'sjohnson@nextthought.com',
                                password=u'temp001')
        user2 = User.create_user(self.ds, username=u'jason@nextthought.com',
                                 password=u'temp001')
        comm = Community(u'AoPS')
        self.ds.root['users'][comm.username] = comm

        user.record_dynamic_membership(comm)
        user2.record_dynamic_membership(comm)
        user.follow(comm)

        note = Note()
        note.containerId = u'foo'
        note.addSharingTarget(comm)
        user2.addContainedObject(note)
        # What really gets shared in the returned value,
        # which may be (is) wrapped in a ContainedProxy
        note = user2.getContainedObject('foo', note.id)

        change = Change(Change.SHARED, note)
        change.creator = 42
        comm._noticeChange(change)

        assert_that(user.getContainedStream('foo'), contains(change))
        # This way we're sure it's the one we have above
        assert_that(user.getContainedStream('foo')[0].creator, is_(42))

        intids = list(user2.iter_intids())
        assert_that(intids, has_length(1))

    @WithMockDSTrans
    def test_getContainedStream_more_items_in_comm_cache_than_cap_returns_newest(self):
        user = User.create_user(self.ds, username=u'sjohnson@nextthought.com',
                                password=u'temp001')
        user2 = User.create_user(self.ds, username=u'jason@nextthought.com',
                                 password=u'temp001')
        comm = Community(u'AoPS')
        self.ds.root['users'][comm.username] = comm
        comm.MAX_STREAM_SIZE = user.MAX_STREAM_SIZE * 3

        user.record_dynamic_membership(comm)
        user2.record_dynamic_membership(comm)
        user.follow(comm)

        def _note_in_foo_at_time_shared_with(x, target):
            note = Note()
            note.containerId = u'foo'
            note.addSharingTarget(target)
            user2.addContainedObject(note)
            note.lastModified = x
            note = user2.getContainedObject(u'foo', note.id)

            change = Change(Change.SHARED, note)
            change.creator = x
            change.lastModified = x
            target._noticeChange(change)
            return change

        # Throw many items in the stream with increasing modification times
        for x in range(0, comm.MAX_STREAM_SIZE):
            change = _note_in_foo_at_time_shared_with(x, comm)

        stream = user.getContainedStream('foo')
        assert_that(stream, has_length(user.MAX_STREAM_SIZE))
        assert_that(stream, has_item(change))
        # This way we're sure it's the one we have above
        assert_that(stream[0].creator, is_(x))

        # also share something newer directly with the user, to verify
        # that sorting comes out as expected
        x = x + 1
        change = _note_in_foo_at_time_shared_with(x, user)

        stream = user.getContainedStream('foo')
        assert_that(stream, has_length(user.MAX_STREAM_SIZE))
        assert_that(stream, has_item(change))
        # This way we're sure it's the one we have above
        assert_that(stream[0].creator, is_(x))
        assert_that(stream[1].creator, is_(x - 1))

    @WithMockDSTrans
    def test_deleting_user_with_contained_objects_removes_intids(self):
        user1 = User.create_user(self.ds, username=u'foo@bar',
                                 password=u'temp001')

        note = Note()
        note.body = [u'text']
        note.containerId = u'c1'
        note.creator = user1.username

        user1.addContainedObject(note)
        assert_that(note.id, is_not(none()))

        intids = component.getUtility(IIntIds)
        assert_that(intids.getId(note), is_not(none()))
        intid = intids.getId(note)

        User.delete_user(user1.username)

        # This works because IObjectRemovedEvent is a type of IObjectMovedEvent,
        # and IObjectMovedEvent is dispatched to sublocations, thanks to
        # zope.container.
        assert_that(intids.queryId(note), is_(none()))
        assert_that(intids.queryObject(intid), is_(none()))

    @WithMockDSTrans
    def test_sublocations_are_set(self):
        user1 = User.create_user(self.ds, username=u'foo@bar',
                                 password=u'temp001')

        note = Note()
        note.body = [u'text']
        note.containerId = u'c1'
        note.creator = user1.username

        user1.addContainedObject(note)

        sublocs = set()

        def _traverse(o):
            assert_that(sublocs, does_not(has_item(o)))
            sublocs.add(o)
            subs = ISublocations(o, None)
            if subs:
                for sub in subs.sublocations():
                    _traverse(sub)

        _traverse(user1)

        assert_that(sublocs, has_item(user1.getContainer(note.containerId)))
        assert_that(sublocs, has_item(user1.friendsLists))

        intids = list(user1.iter_intids())
        assert_that(intids, has_length(1))

    @unittest.skip("Annotations disabled for now; causes problems with indexing.")
    @WithMockDSTrans
    def test_sublocations_include_annotations(self):
        user1 = User.create_user(self.ds, username=u'foo@bar',
                                 password=u'temp001')

        import nti.chatserver.messageinfo as chat_msg
        import nti.chatserver.interfaces as chat_interfaces

        msg_info = chat_msg.MessageInfo()
        msg_info.creator = user1.username
        msg_info.containerId = u'c1'

        storage = chat_interfaces.IMessageInfoStorage(msg_info)
        storage.add_message(msg_info)

        sublocs = set()
        for x in user1.sublocations():
            assert_that(sublocs, does_not(has_item(x)))
            sublocs.add(x)

        assert_that(sublocs, has_item(storage))
        intids = component.getUtility(IIntIds)
        assert_that(intids.getId(msg_info), is_not(none()))
        intid = intids.getId(msg_info)

        # Deleting the user clears this intid too
        User.delete_user(user1.username)
        assert_that(intids.queryId(msg_info), is_(none()))
        assert_that(intids.queryObject(intid), is_(none()))

    @WithMockDSTrans
    def test_resolve_by_ntiid(self):
        user1 = User.create_user(mock_dataserver.current_mock_ds,
                                 username=u'foo@bar')
        comm = Community.get_entity(username=u'Everyone')

        assert_that(find_object_with_ntiid(user1.NTIID), is_(user1))
        assert_that(find_object_with_ntiid(comm.NTIID), is_(comm))

        assert_that(comm.NTIID,
                    is_(not_none()))
        assert_that(to_external_object(comm),
                    has_entry('NTIID', not_none()))

        # Lowercasing it works too...
        assert_that(find_object_with_ntiid(user1.NTIID.lower()),
                    is_(user1))

    @WithMockDS
    def test_owned_dfls_in_xxx_intids(self):
        with mock_dataserver.mock_db_trans(self.ds):
            user1 = User.create_user(self.ds, username=u'foo@bar',
                                     password=u'temp001')
            user2 = User.create_user(self.ds, username=u'fab@bar',
                                     password=u'temp001')

            friends_list = DynamicFriendsList(username='Friends')
            friends_list.creator = user1
            user1.addContainedObject(friends_list)
            friends_list.addFriend(user2)

            assert_that(list(user1.xxx_intids_of_memberships_and_self),
                        has_item(friends_list._ds_intid))


from zope.event import notify

from nti.apns.interfaces import APNSDeviceFeedback


class TestFeedbackEvent(DataserverLayerTest):

    layer = mock_dataserver.SharedConfiguringTestLayer

    @WithMockDSTrans
    def test_devicefeedback(self):
        user = User.create_user(self.ds, username=u'sjohnson@nextthought.com',
                                password=u'temp001')
        deviceid = b'b' * 32
        device = user.maybeCreateContainedObjectWithType(
            'Devices', deviceid.encode('hex')
        )
        user.addContainedObject(device)
        assert_that(user.devices, has_value(device))
        assert_that(user.devices, has_length(1))

        event = APNSDeviceFeedback(5, deviceid)
        notify(event)

        assert_that(user.devices, has_length(0))


import zope.schema.interfaces


class TestUserNotDevMode(mock_dataserver.NotDevmodeDataserverLayerTest):

    features = ()

    @WithMockDS
    def test_update_existing_created_without_email(self):
        with mock_dataserver.mock_db_trans(self.ds):
            user = User.create_user(self.ds, username=u'sjohnson@nextthought.com',
                                    password=u'temp001')
            # with an mtime of None we cannot create invalid
            with assert_raises(zope.schema.interfaces.RequiredMissing):
                update_from_external_object(user, {})

        with mock_dataserver.mock_db_trans(self.ds):
            user = User.get_user('sjohnson@nextthought.com')
            # But once we're saved there is no use harping on required missing
            # data; presumably the profile changed
            assert_that(user._p_mtime, greater_than(0))
            update_from_external_object(user, {})


from hamcrest import contains_inanyorder

from nti.testing.matchers import validly_provides


class TestCommunity(DataserverLayerTest):

    layer = mock_dataserver.SharedConfiguringTestLayer

    @WithMockDSTrans
    def test_community_admin(self):
        user = User.create_user(self.ds, username=u'sjohnson@nextthought.com',
                                password=u'temp001')
        user2 = User.create_user(self.ds, username=u'jason@nextthought.com',
                                 password=u'temp001')
        comm = Community.create_entity(self.ds, username=u'AoPS')

        user.record_dynamic_membership(comm)
        user2.record_dynamic_membership(comm)

        assert_that(comm.get_admin_usernames(), has_length(0))

        # Test add
        comm.add_admin(user)
        assert_that(comm.get_admin_usernames(), has_length(1))
        assert_that(comm.is_admin(user), is_(True))
        assert_that(comm.is_admin(user2), is_(False))

        # Test remove
        comm.remove_admin(user)
        assert_that(comm.get_admin_usernames(), has_length(0))
        assert_that(comm.is_admin(user), is_(False))
        assert_that(comm.is_admin(user2), is_(False))

        # Test remove twice
        comm.remove_admin(user2)
        assert_that(comm.get_admin_usernames(), has_length(0))
        assert_that(comm.is_admin(user), is_(False))
        assert_that(comm.is_admin(user2), is_(False))

    @WithMockDSTrans
    def test_community_enumarable_adapter(self):
        user = User.create_user(self.ds, username=u'sjohnson@nextthought.com',
                                password=u'temp001')
        user2 = User.create_user(self.ds, username=u'jason@nextthought.com',
                                 password=u'temp001')
        comm = Community.create_entity(self.ds, username=u'AoPS')

        user.record_dynamic_membership(comm)
        user2.record_dynamic_membership(comm)

        container = IEntityContainer(comm)
        assert_that(container,
                    validly_provides(ILengthEnumerableEntityContainer,
                                     IIntIdIterable))

        assert user in container
        assert user2 in container
        assert_that(container, has_length(2))

        assert_that(container.iter_intids(),
                    contains_inanyorder(user._ds_intid, user2._ds_intid))

    @WithMockDSTrans
    def test_delete_community_clears_memberships(self):
        user = User.create_user(self.ds, username=u'sjohnson@nextthought.com',
                                password=u'temp001')
        user2 = User.create_user(self.ds, username=u'jason@nextthought.com',
                                 password=u'temp001')
        comm = Community.create_entity(self.ds, username=u'AoPS')

        user.record_dynamic_membership(comm)
        user2.record_dynamic_membership(comm)

        assert_that(user, is_in(comm))
        assert_that(user2, is_in(comm))
        assert_that(comm, is_in(user.dynamic_memberships))
        assert_that(comm, is_in(user2.dynamic_memberships))

        Community.delete_entity(comm.username, self.ds)

        assert_that(user, is_not(is_in(comm)))
        assert_that(user2, is_not(is_in(comm)))
        assert_that(comm, is_not(is_in(user.dynamic_memberships)))
        assert_that(comm, is_not(is_in(user2.dynamic_memberships)))
