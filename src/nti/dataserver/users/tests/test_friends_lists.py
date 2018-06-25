#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import is_in
from hamcrest import contains
from hamcrest import has_item
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_property
from hamcrest import same_instance
from hamcrest import is_not as does_not
from hamcrest import contains_inanyorder
from hamcrest import greater_than_or_equal_to
from hamcrest import greater_than
is_not = does_not

from nti.testing.matchers import is_true
from nti.testing.matchers import is_false
from nti.testing.matchers import validly_provides

from nti.testing.time import time_monotonically_increases

import fudge

from zope import component

from zope.intid.interfaces import IIntIds

from nti.contentrange.contentrange import ContentRangeDescription

from nti.dataserver import authorization as nauth

from nti.dataserver.contenttypes import Note

from nti.dataserver.interfaces import IIntIdIterable
from nti.dataserver.interfaces import IEntityContainer
from nti.dataserver.interfaces import ILengthEnumerableEntityContainer

from nti.dataserver.users.friends_lists import FriendsList
from nti.dataserver.users.friends_lists import DynamicFriendsList

from nti.dataserver.users.users import User

from nti.externalization.externalization import to_external_object
from nti.externalization.internalization import update_from_external_object

from nti.ntiids.oids import to_external_ntiid_oid

from zope.component import eventtesting

from nti.dataserver.tests.mock_dataserver import WithMockDS, WithMockDSTrans

from nti.dataserver.tests import mock_dataserver

from nti.dataserver.tests.mock_dataserver import DataserverLayerTest

from nti.dataserver.tests.test_authorization_acl import denies
from nti.dataserver.tests.test_authorization_acl import permits


class TestFriendsLists(DataserverLayerTest):

    @time_monotonically_increases
    def test_update_friends_list_name(self):
        class O(object):
            username = u'foo'
            _avatarURL = u'BAD'
        o = FriendsList(u'MyList')
        modified = o.modified
        ntiid = o.NTIID
        ext_value = to_external_object(o)
        assert_that(ext_value, has_entry('Username', 'MyList'))
        assert_that(ext_value, has_entry('alias', 'MyList'))
        assert_that(ext_value, has_entry('realname', 'MyList'))

        update_from_external_object(o, {'realname': u"My Funny Name"})

        assert_that(o.modified, greater_than(modified))

        ext_value = to_external_object(o)

        assert_that(ext_value, has_entry('Username', 'MyList'))
        assert_that(ext_value, has_entry('realname', 'My Funny Name'))
        assert_that(ext_value, has_entry('alias', 'My Funny Name'))

        # NTIID didn't change
        assert_that(o.NTIID, is_(ntiid))
        # in fact its cached
        assert_that(o.NTIID, is_(same_instance(ntiid)))

        # Username changing changes it though
        o.creator = O()
        assert_that(o.NTIID, is_not(ntiid))

    @WithMockDSTrans
    def test_update_friends_list(self):
        owner = User.create_user(username=u'owner@bar')
        user =  User.create_user(username=u'1foo@bar')
        user2 = User.create_user(username=u'2foo2@bar')
        user3 = User.create_user(username=u'3foo3@bar')
        user4 = User.create_user(username=u'4foo4@bar')
        user5 = User.create_user(username=u'5foo5@bar')
        user6 = User.create_user(username=u'6foo6@bar')
        user7 = User.create_user(username=u'7foo7@bar')
        user8 = User.create_user(username=u'8foo8@BAR')

        fl = FriendsList(u'MyList')
        fl.creator = owner

        # Cannot add self
        fl.updateFromExternalObject({'friends': [owner]})
        assert_that(list(fl), has_length(0))

        # Can add a few to empty
        fl.updateFromExternalObject({'friends': [user, user2]})
        assert_that(list(fl), has_length(2))
        assert_that(sorted(fl), contains(user, user2))

        # Can add one more
        fl.updateFromExternalObject(
            {'friends': [user, user2, user3, user, user2, user3]})
        assert_that(list(fl), has_length(3))
        assert_that(sorted(fl), contains(user, user2, user3))

        # Can go back to one
        fl.updateFromExternalObject({'friends': [user2]})
        assert_that(list(fl), has_length(1))
        assert_that(list(fl), contains(user2))

        fl.updateFromExternalObject({'friends': [user]})
        assert_that(list(fl), contains(user))

        fl.updateFromExternalObject({
            'friends': [user, user2, user3, user, user2, user3]
        })
        assert_that(list(fl), has_length(3))
        assert_that(sorted(fl), contains(user, user2, user3))

        updated = fl.updateFromExternalObject({
            'friends': [user.username, user2.username, user3.username, user4.username]
        })
        assert_that(updated, is_true())
        assert_that(list(fl), has_length(4))
        assert_that(sorted(fl), contains(user, user2, user3, user4))

        updated = fl.updateFromExternalObject(
            {'friends': [user4.username, user3.username, user2.username, user.username]
        })
        assert_that(updated, is_false())  # no change

        updated = fl.updateFromExternalObject({
            'friends': [user.username, user2.username, user3.username, user4.username,
                        user5.username, user6.username]
        })
        assert_that(updated, is_true())
        assert_that(list(fl), has_length(6))
        assert_that(sorted(fl), contains(
            user, user2, user3, user4, user5, user6))

        updated = fl.updateFromExternalObject({
            'friends': [user.username, user2.username, user3.username, user4.username,
                        user5.username, user6.username, user7.username, user8.username]
        })
        assert_that(updated, is_true())
        assert_that(list(fl), has_length(8))
        assert_that(sorted(fl), contains(user, user2, user3,
                                         user4, user5, user6, user7, user8))

        # Break some refs
        User.delete_user(user.username)

        updated = fl.updateFromExternalObject({
            'friends': [user.username, user2.username, user3.username, user4.username,
                        user5.username, user6.username, user7.username, user8.username]
        })
        assert_that(updated, is_true())
        assert_that(list(fl), has_length(7))
        assert_that(sorted(fl), 
                    contains(user2, user3, user4, user5, user6, user7, user8))

    @WithMockDS
    def test_create_update_dynamic_friendslist(self):
        ds = mock_dataserver.current_mock_ds
        with mock_dataserver.mock_db_trans(ds):
            user1 = User.create_user(ds, username=u'foo23')
            user2 = User.create_user(ds, username=u'foo12')
            user3 = User.create_user(ds, username=u'foo13')

            fl1 = DynamicFriendsList(username=u'Friends')
            fl1.creator = user1  # Creator must be set

            user1.addContainedObject(fl1)
            fl1.addFriend(user2)

            assert_that(user2.dynamic_memberships, has_item(fl1))
            assert_that(user2.entities_followed, has_item(fl1))

        for u in user1, user2, user3:
            u._p_deactivate()
            u._p_invalidate()
            assert_that(u, has_property('__dict__', {}))

        with mock_dataserver.mock_db_trans(ds):
            # This process actually activates the objects directly, immediately, during the
            # iteration process
            fl1.updateFromExternalObject({'friends': [user3.username]})

            assert_that(user3.dynamic_memberships, has_item(fl1))

            assert_that(user2.dynamic_memberships, does_not(has_item(fl1)))
            assert_that(user2.entities_followed, does_not(has_item(fl1)))

            # The external form masquerades as a normal FL...
            x = to_external_object(fl1)
            assert_that(x, has_entry('Class', 'DynamicFriendsList'))
            assert_that(x, 
                        has_entry('MimeType', 'application/vnd.nextthought.dynamicfriendslist'))
            assert_that(x, 
                        has_entry('NTIID', 'tag:nextthought.com,2011-10:foo23-MeetingRoom:Group-friends'))
            assert_that(x, has_entry('Locked', is_(False)))
            # ... with one exception
            assert_that(x, has_entry('IsDynamicSharing', True))

    @WithMockDSTrans
    def test_delete_dynamic_friendslist_clears_memberships(self):
        ds = mock_dataserver.current_mock_ds
        user1 = User.create_user(ds, username=u'foo23')
        user2 = User.create_user(ds, username=u'foo12')

        fl1 = DynamicFriendsList(username=u'Friends')
        fl1.creator = user1  # Creator must be set

        user1.addContainedObject(fl1)
        fl1.addFriend(user2)

        assert_that(list(user2.dynamic_memberships), has_item(fl1))
        assert_that(list(user2.entities_followed), has_item(fl1))

        eventtesting.clearEvents()
        assert_that(user1.deleteContainedObject(fl1.containerId, fl1.id),
                    is_(fl1))

        # If the events don't fire correctly, the weakref will still have this cached
        # so it will still seem to be present
        assert_that(list(user2.dynamic_memberships), does_not(has_item(fl1)))
        assert_that(list(user2.entities_followed), does_not(has_item(fl1)))
        assert_that(user2, has_property('_dynamic_memberships', has_length(1)))


def _note_from(creator, text=u'Hi there', containerId=u'tag:nti'):
    owner_note = Note()
    owner_note.applicableRange = ContentRangeDescription()
    owner_note.creator = creator
    owner_note.body = [text]
    owner_note.containerId = containerId
    return owner_note


def _dfl_sharing_fixture(unused_ds, owner_username=u'OwnerUser@bar', passwords=None):
    """
    Create a user owning a DFL. Two other users are added to the dfl.

    :return: A tuple (owner, member1, member2, dfl)
    """

    password_kwargs = {}
    if passwords:
        password_kwargs = {'password': passwords}
    # Create a user with a DFL and two friends in the DFL
    owner_user = User.create_user(username=owner_username, 
                                  **password_kwargs)
    parent_dfl = DynamicFriendsList(username=u"ParentFriendsList")
    parent_dfl.creator = owner_user
    owner_user.addContainedObject(parent_dfl)

    member_user = User.create_user(username=u"memberuser@bar",
                                    **password_kwargs)
    parent_dfl.addFriend(member_user)

    member_user2 = User.create_user(username=u"memberuser2@bar", 
                                    **password_kwargs)
    parent_dfl.addFriend(member_user2)

    # Reset notification counts (Circled notices would have gone out)
    for u in (owner_user, member_user, member_user2):
        u.notificationCount.value = 0

    return owner_user, member_user, member_user2, parent_dfl


def _assert_that_item_is_in_contained_stream_and_data_with_notification_count(user, item, count=1):
    __traceback_info__ = user, item
    child_stream = user.getContainedStream(item.containerId)
    assert_that(child_stream, has_length(count))
    assert_that(child_stream, 
                 has_item(has_property('object', item)), "stream has right item")
    assert_that(user.notificationCount, 
                has_property('value', count), "notification count has right size")

    shared_data = user.getSharedContainer(item.containerId)
    assert_that(shared_data, has_item(item), "item is in shared data")
    assert_that(shared_data, 
                 has_length(greater_than_or_equal_to(count)), "shared data has right size")


class TestDFL(DataserverLayerTest):

    @WithMockDSTrans
    def test_dfl_container(self):
        owner = User.create_user(username=u'owner@bar')
        user = User.create_user(username=u'1foo@bar')
        user2 = User.create_user(username=u'2foo2@bar')
        user3 = User.create_user(username=u'3foo3@bar')
        user4 = User.create_user(username=u'4foo4@bar')
        user5 = User.create_user(username=u'5foo5@bar')
        user6 = User.create_user(username=u'6foo6@bar')
        user7 = User.create_user(username=u'7foo7@bar')
        user8 = User.create_user(username=u'8foo8@BAR')

        all_users = (user, user2, user3, user4, user5, user6, user7, user8)

        fl = DynamicFriendsList(u'MyList')
        # Needs an intid before we can add people to it
        component.getUtility(IIntIds).register(fl)
        fl.creator = owner
        for x in all_users:
            fl.addFriend(x)

        container = IEntityContainer(fl)
        assert_that(container,
                    validly_provides(ILengthEnumerableEntityContainer,
                                     IIntIdIterable))

        members = all_users + (owner,)
        for x in members:
            __traceback_info__ = x
            assert x in container

        assert_that(container, has_length(8))

        assert_that(container.iter_intids(),
                    contains_inanyorder(*(x._ds_intid for x in members)))
        assert_that(list(container),
                    contains_inanyorder(*members))

    @WithMockDSTrans
    def test_dfl_internal(self):
        fl = DynamicFriendsList(u'MyList')
        component.getUtility(IIntIds).register(fl)
        fl.About = u'my list'
        fl.Locked = True

        ext_obj = to_external_object(fl)
        assert_that(ext_obj, has_entry('About', 'my list'))
        assert_that(ext_obj, has_entry('about', 'my list'))
        assert_that(ext_obj, has_entry('Locked', is_(True)))

        # Only the lowercase update will work
        ext_obj['locked'] = False
        ext_obj['about'] = u'foo list'
        update_from_external_object(fl, ext_obj)

        assert_that(fl, has_property('About', 'foo list'))
        assert_that(fl, has_property('about', 'foo list'))
        assert_that(fl, has_property('Locked', is_(False)))

    @WithMockDS
    @fudge.patch('nti.dataserver.activitystream.hasQueryInteraction')
    def test_sharing_with_dfl(self, mock_hqi):
        mock_hqi.is_callable().with_args().returns(True)
        ds = mock_dataserver.current_mock_ds
        with mock_dataserver.mock_db_trans(ds):
            owner_user, member_user, member_user2, parent_dfl = _dfl_sharing_fixture(ds)

            with owner_user.updates():
                # Create a note
                owner_note = _note_from(owner_user)

                # (Check base states)
                for u in (member_user, member_user2):
                    child_stream = u.getContainedStream(owner_note.containerId)
                    assert_that(child_stream, has_length(0))

                # Share the note with the DFL and thus its two members
                owner_note.addSharingTarget(parent_dfl)
                owner_user.addContainedObject(owner_note)

            # Sharing with the DFL caused broadcast events and notices to go out
            # to the members of the DFL. These members have the shared object
            # in their stream and shared data
            for u in (member_user, member_user2):
                _assert_that_item_is_in_contained_stream_and_data_with_notification_count(u, owner_note)

            # If a member of the DFL replies to the note,
            # then the same thing happens,
            with member_user.updates():
                child_note = _note_from(member_user, u'A reply')

                ext_obj = to_external_object(child_note)
                ext_obj['inReplyTo'] = to_external_ntiid_oid(owner_note)

                update_from_external_object(child_note, ext_obj, context=ds)

                assert_that(child_note, has_property('inReplyTo', owner_note))
                assert_that(child_note,
                            has_property('sharingTargets', set((parent_dfl, owner_user))))

                member_user.addContainedObject(child_note)

            # Notices go out to the other members of the DFL, including the
            # owner
            _assert_that_item_is_in_contained_stream_and_data_with_notification_count(member_user2, child_note, 2)
            _assert_that_item_is_in_contained_stream_and_data_with_notification_count(owner_user, child_note, 1)

    @WithMockDS
    @fudge.patch('nti.dataserver.activitystream.hasQueryInteraction')
    def test_sharing_with_dfl_member_shares_top_level(self, mock_hqi):
        """
        If a member of the DFL shares something unrelated with the DFL,
        it is visible to the creator of the DFL in the shared data, in the stream, and
        in the notification count. It is also in the 'iterntiids' value for all
        people.

        Validates the DFL sharing architecture.
        """
        mock_hqi.is_callable().with_args().returns(True)
        ds = mock_dataserver.current_mock_ds
        with mock_dataserver.mock_db_trans(ds):
            owner_user, member_user, member_user2, parent_dfl = _dfl_sharing_fixture(ds)

            # A second DFL with the same username
            parent_dfl2 = DynamicFriendsList(username=parent_dfl.username)
            owner_user2 = User.create_user(username=u"owneruser2@bar")
            parent_dfl2.creator = owner_user2
            owner_user2.addContainedObject(parent_dfl2)

            with member_user.updates():
                child_note = _note_from(member_user, u'From the child')
                child_note.addSharingTarget(parent_dfl)

                assert_that(child_note,
                             has_property('sharingTargets', set((parent_dfl,))))

                member_user.addContainedObject(child_note)

            # The shared note is in the shared data for the owner of the DFL
            # And in the stream of the owner of the DFL
            # and as a notification for the DFL owner
            _assert_that_item_is_in_contained_stream_and_data_with_notification_count(owner_user, child_note, 1)

            # and is in the other member's stream and shared data as well
            _assert_that_item_is_in_contained_stream_and_data_with_notification_count(member_user2, child_note, 1)

            # This Note provides ACL access to its creator and the members/owner ,
            # of the DFL, but not a DFL with the same name.
            # DFL resolves to NTIID of owner + dfl-username.
            assert_that(child_note, permits(member_user, nauth.ACT_READ))
            assert_that(child_note, permits(parent_dfl, nauth.ACT_READ))
            assert_that(child_note, denies(parent_dfl2, nauth.ACT_READ))

            # Even though the other members do not have data in this NTIID, they
            # still register that they are interested in it
            for member in (owner_user, member_user, member_user2):
                ids = list(member.iterntiids())
                __traceback_info__ = member, ids
                assert_that(ids, contains(child_note.containerId))

                intids = list(member.iter_intids())
                assert_that(intids, has_length(greater_than_or_equal_to(1)))

    @WithMockDS
    @fudge.patch('nti.dataserver.activitystream.hasQueryInteraction')
    def test_replace_dfl_sharing_with_a_member(self, mock_hqi):
        """
        After removing the DFL share from a note and replace it with a direct sharing
        of a DFL member, make sure the note is still accessible
        """
        mock_hqi.is_callable().with_args().returns(True)
        ds = mock_dataserver.current_mock_ds
        with mock_dataserver.mock_db_trans(ds):
            jmadden = User.create_user(username=u'jmadden@nextthought.com')
            sjohnson = User.create_user(username=u'sjohnson@nextthought.com')

            ntusrs = DynamicFriendsList(username=u'ntusrs')
            ntusrs.creator = jmadden
            jmadden.addContainedObject(ntusrs)
            ntusrs.addFriend(sjohnson)

            note = Note()
            note.body = [u'Violent Blades']
            note.creator = jmadden.username
            note.containerId = u'c1'

            with jmadden.updates():
                note.addSharingTarget(ntusrs)
                note = jmadden.addContainedObject(note)

            scnt = sjohnson.getSharedContainer(u'c1')
            assert_that(note, is_in(scnt))

            with jmadden.updates():
                note = jmadden.getContainedObject(u'c1', note.id)
                note.clearSharingTargets()
                note.addSharingTarget(sjohnson)

            scnt = sjohnson.getSharedContainer(u'c1')
            assert_that(note, is_in(scnt))

    @WithMockDSTrans
    def test_remove_friends(self):
        owner = User.create_user(username=u'owner@bar')
        fl1 = DynamicFriendsList(username=u'Friends')
        fl1.creator = owner
        owner.addContainedObject(fl1)

        collected = []
        for x in range(100):
            user = User.create_user(username=u'%sfoo@bar' % x)
            fl1.addFriend(user)
            collected.append(user)

        result = fl1.removeFriends(*collected[50:])
        assert_that(result, is_(50))
        assert_that(fl1, has_length(50))

        for user in collected[50:]:
            assert_that(user, does_not(is_in(fl1)))

        for user in collected[0:50]:
            assert_that(user, is_in(fl1))
