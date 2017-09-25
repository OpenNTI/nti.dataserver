#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import has_key
from hamcrest import contains
from hamcrest import has_item
from hamcrest import not_none
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_entries
from hamcrest import has_property
from hamcrest import same_instance
from hamcrest import only_contains

from nti.testing.matchers import is_true
from nti.testing.matchers import is_empty
from nti.testing.matchers import provides

import os
import six
import time
import tempfile

import transaction

from zope import component
from zope import interface

from zope.annotation.interfaces import IAttributeAnnotatable

from zope.intid.interfaces import IIntIds

from ZODB.DB import DB

from ZODB.interfaces import IConnection

from pyramid.interfaces import IAuthenticationPolicy

from nti.appserver.pyramid_authorization import ACLAuthorizationPolicy

from nti.chatserver._handler import _ChatHandler

from nti.chatserver.chatserver import Chatserver
from nti.chatserver.chatserver import TestingMappingMeetingStorage

from nti.chatserver.interfaces import ACT_ENTER
from nti.chatserver.interfaces import ACT_MODERATE
from nti.chatserver.interfaces import CHANNEL_META
from nti.chatserver.interfaces import CHANNEL_POLL
from nti.chatserver.interfaces import CHANNEL_STATE
from nti.chatserver.interfaces import CHANNEL_CONTENT
from nti.chatserver.interfaces import CHANNEL_DEFAULT
from nti.chatserver.interfaces import CHANNEL_WHISPER

from nti.chatserver.interfaces import IChatserver
from nti.chatserver.interfaces import IMessageInfoStorage

from nti.chatserver.meeting import _Meeting

from nti.chatserver.messageinfo import MessageInfo

from nti.chatserver.presenceinfo import PresenceInfo

from nti.contentfragments.interfaces import IPlainTextContentFragment

from nti.dataserver import authorization as auth

from nti.dataserver import authorization_acl as auth_acl

from nti.dataserver.chat_transcripts import _transcript_ntiid
from nti.dataserver.chat_transcripts import list_transcripts_for_user
from nti.dataserver.chat_transcripts import transcript_for_user_in_room
from nti.dataserver.chat_transcripts import transcript_summaries_for_user_in_container

from nti.dataserver.contenttypes import Note

from nti.dataserver.interfaces import ITranscript

from nti.dataserver.users.users import User
from nti.dataserver.users.users import get_shared_dataserver as _get_shared_dataserver

from nti.externalization.externalization import EXT_FORMAT_JSON
from nti.externalization.externalization import toExternalObject
from nti.externalization.externalization import NonExternalizableObjectError

from nti.externalization.internalization import update_from_external_object

from nti.externalization.representation import to_external_representation
from nti.externalization.representation import to_json_representation_externalized

from nti.links.links import Link

from nti.ntiids.ntiids import ROOT
from nti.ntiids.ntiids import TYPE_TRANSCRIPT
from nti.ntiids.ntiids import TYPE_TRANSCRIPT_SUMMARY

from nti.ntiids.ntiids import get_type
from nti.ntiids.ntiids import make_ntiid
from nti.ntiids.ntiids import find_object_with_ntiid

from nti.ntiids.oids import toExternalOID
from nti.ntiids.oids import to_external_ntiid_oid

from nti.socketio.interfaces import ISocketSession
from nti.socketio.interfaces import ISocketIOSocket
from nti.socketio.interfaces import ISocketEventHandler

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.dataserver.tests import mock_dataserver

from nti.dataserver.tests.test_authorization_acl import denies
from nti.dataserver.tests.test_authorization_acl import permits

from nti.dataserver.tests.mock_dataserver import WithMockDS
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans
from nti.dataserver.tests.mock_dataserver import DataserverLayerTest


class chat(object):

    Meeting = _Meeting
    MessageInfo = MessageInfo
    ModeratedMeeting = _Meeting

    Chatserver = Chatserver
    ChatHandler = _ChatHandler
    TestingMappingMeetingStorage = TestingMappingMeetingStorage

    CHANNEL_POLL = CHANNEL_POLL
    CHANNEL_META = CHANNEL_META
    CHANNEL_STATE = CHANNEL_STATE
    CHANNEL_CONTENT = CHANNEL_CONTENT
    CHANNEL_DEFAULT = CHANNEL_DEFAULT
    CHANNEL_WHISPER = CHANNEL_WHISPER


class TestChatRoom(DataserverLayerTest):

    def setUp(self):
        super(TestChatRoom, self).setUp()
        component.provideUtility(ACLAuthorizationPolicy())

    @WithMockDSTrans
    def test_become_moderated(self):
        User.create_user(username=u'sjohnson@nti')
        room = chat.Meeting(None)
        assert_that(room.Moderated, is_(False))
        room.Moderated = True
        room.id = u'foo'
        assert_that(room, is_(chat.ModeratedMeeting))

        msg = chat.MessageInfo()
        msg.creator = u'sjohnson@nti'
        room.post_message(msg)
        assert_that(room._moderation_state._moderation_queue,
                    has_key(msg.MessageId))

        # We can externalize a moderated room
        to_external_representation(room, EXT_FORMAT_JSON)

    def test_persist_moderated_stays_moderated(self):
        # We can start with a regular room, persist it,
        # make it moderated, persist, then load it back as moderated
        from ZODB.FileStorage import FileStorage  # defer import, only used here

        tmp_dir = tempfile.mkdtemp()
        fs = FileStorage(os.path.join(tmp_dir, "data.fs"))
        db = DB(fs)
        conn = db.open()
        room = chat.Meeting(None)
        assert_that(room.Moderated, is_(False))
        conn.root()['Room'] = room
        transaction.commit()
        conn.close()
        db.close()

        fs = FileStorage(os.path.join(tmp_dir, "data.fs"))
        db = DB(fs)
        conn = db.open()
        room = conn.root()['Room']
        room.Moderated = True
        transaction.commit()
        conn.close()
        db.close()

        # Should still be moderated.
        fs = FileStorage(os.path.join(tmp_dir, "data.fs"))
        db = DB(fs)
        conn = db.open()
        room = conn.root()['Room']
        # Our hacky workaround only comes into play after the first
        # time an attribute is accessed and we de-ghost the object.
        assert_that(room, is_(chat.Meeting))
        # A method attribute, not an ivar, triggers this
        assert_that(room.post_message.im_func,
                    is_(chat.ModeratedMeeting.post_message.im_func))
        assert_that(room._moderation_state,
                    has_property('_moderated_by_names', not_none()))
        # Now, we can reverse the property
        room.Moderated = False
        assert_that(room, is_(chat.Meeting))
        transaction.commit()
        conn.close()
        db.close()

        # Should still be moderated.
        fs = FileStorage(os.path.join(tmp_dir, "data.fs"))
        db = DB(fs)
        conn = db.open()
        room = conn.root()['Room']
        assert_that(room, is_(chat.Meeting))
        assert_that(room.post_message.im_class,
                    is_(same_instance(chat.Meeting)))
        transaction.commit()
        conn.close()
        db.close()

    @WithMockDS
    def test_external_reply_to_different_storage(self):
        ds = self.ds
        with mock_dataserver.mock_db_trans(ds) as conn:
            n = Note()
            room = chat.Meeting(None)
            conn.add(n)
            component.getUtility(IIntIds).register(n)
            mock_dataserver.add_memory_shard(ds, 'Sessions')
            sconn = conn.get_connection('Sessions')
            sconn.add(room)
            room.inReplyTo = n
            room.addReference(n)
            conn.root()['Notes'] = [n]
            sconn.root()['Notes'] = [room]
            n_ext_id = to_external_ntiid_oid(n)

        with mock_dataserver.mock_db_trans(ds):
            ext = room.toExternalObject()
            assert_that(ext, has_entry('inReplyTo', n_ext_id))
            assert_that(ext, has_entry('references', only_contains(n_ext_id)))
            assert_that(ext, has_entry('Moderators', []))
            assert_that(ext, has_entry('MessageCount', 0))
            assert_that(ext, has_entry('Moderated', False))
            to_external_representation(room, EXT_FORMAT_JSON)

        with mock_dataserver.mock_db_trans(ds):
            room.inReplyTo = None
            room.clearReferences()
            assert_that(room.inReplyTo, none())

        with mock_dataserver.mock_db_trans(ds):
            room = chat.Meeting(None)
            update_from_external_object(room, ext, context=ds)
            assert_that(room.inReplyTo, is_(n))
            assert_that(room.references[0], is_(n))

        ds.close()

    @WithMockDSTrans
    def test_approve_moderated_removes_from_queue(self):
        User.create_user(username=u'sjohnson@nti')

        class MockChatServer(object):
            def _save_message_to_transcripts(self, *args, **kwargs):
                pass

        room = chat.Meeting(MockChatServer())
        room.Moderated = True
        room.id = u'foo:bar'
        assert_that(room, is_(chat.ModeratedMeeting))
        assert_that(room.toExternalObject(), has_entry('Moderated', True))

        msg = chat.MessageInfo()
        msg.containerId = room.id
        msg.creator = u'sjohnson@nti'
        room.post_message(msg)
        assert_that(room._moderation_state._moderation_queue,
                    has_key(msg.MessageId))

        room.approve_message(msg.MessageId)
        assert_that(room._moderation_state._moderation_queue,
                    is_not(has_key(msg.MessageId)))


class _ChatserverTestMixin(object):

    class PH(object):
        def __init__(self, strict_events=False):
            self.events = []
            self.strict_events = strict_events

        def send_event(self, name, *args):
            event = {'name': name, 'args': args}
            if self.strict_events:
                # See socketio.protocol
                to_json_representation_externalized(event)
            self.events.append(event)

    @interface.implementer(ISocketSession, IAttributeAnnotatable)
    class MockSession(object):
        def __init__(self, owner, strict_events=False):
            self.socket = TestChatserver.PH(strict_events=strict_events)
            self.owner = owner
            self.creation_time = time.time()
            self.session_id = None

        def __conform__(self, iface):
            if iface == ISocketIOSocket:
                return self.socket
            return None

    Session = MockSession

    class Sessions(object):

        def __init__(self):
            self.sessions = {}

        def __delitem__(self, k):
            del self.sessions[k]

        def __setitem__(self, k, v):
            self.sessions[k] = v
            v.session_id = k
            if not User.get_user(v.owner):
                username = v.owner
                if '@' not in v.owner:
                    username = v.owner + u'@nextthought.com'
                user = User.create_user(username=username)
                # Establish an alias if '@' wasn't in the name
                _get_shared_dataserver().root['users'][v.owner] = user
            v.the_user = User.get_user(v.owner)

        def __getitem__(self, k):
            return self.sessions[k]

        def __len__(self):
            return len(self.sessions)

        def __iter__(self):
            return self.sessions.itervalues()

        def get_session(self, sid):
            try:
                return self.sessions[sid]
            except KeyError:
                return None

        def get_sessions_by_owner(self, owner):
            return [x for x in self.sessions.values() if x.owner == owner]

        def get_session_by_owner(self, *args, **kwargs):
            # XXX Sort of a hack
            from nti.dataserver.sessions import SessionService
            im_func = six.get_method_function(SessionService.get_session_by_owner)
            return im_func(self, *args, **kwargs)

        def send_event_to_user(self, *args, **kwargs):
            # XXX Sort of a hack
            from nti.dataserver.sessions import SessionService
            im_func = six.get_method_function(SessionService.send_event_to_user)
            return im_func(self, *args, **kwargs)

        def clear_all_session_events(self):
            for session in self:
                del session.socket.events[:]

    def _create_room(self, otherDict=None, meeting_storage_factory=chat.TestingMappingMeetingStorage):
        """
        Returns a room.
        """
        sessions = self.Sessions()
        sessions[1] = self.Session('sjohnson')
        sessions[2] = self.Session('chris')
        sessions[3] = self.Session('jason')
        self.sessions = sessions
        chatserver = chat.Chatserver(sessions, meeting_storage_factory())

        component.provideUtility(chatserver)

        d = {'Occupants': [u'jason', u'chris', u'sjohnson'],
             'ContainerId': u'tag:nextthought.com,2011-10:x-y-z',
             'Creator': u'sjohnson'}
        if otherDict:
            d.update(otherDict)
        room = chatserver.create_room_from_dict(d)
        ids = component.getUtility(IIntIds)
        if not ids.queryId(room):
            ids.register(room)
        return room, chatserver

    def _create_moderated_room(self, otherDict=None):
        """
        Returns a room moderated by sjohnson.
        """
        room, chatserver = self._create_room(otherDict)
        room.Moderated = True
        room.add_moderator('sjohnson')  # sjohnson moderates
        assert_that(room.Moderated, is_(True))
        assert_that(room.Moderators, is_(set(['sjohnson'])))
        return room, chatserver


class TestChatserver(DataserverLayerTest, _ChatserverTestMixin):

    def setUp(self):
        super(TestChatserver, self).setUp()
        component.provideUtility(ACLAuthorizationPolicy())

    @WithMockDSTrans
    def test_handler_shadow_user(self):
        room, chatserver = self._create_moderated_room()
        sjohn_handler = chat.ChatHandler(chatserver, self.sessions[1])
        room.__acl__ = ()  # override the provider
        assert_that(sjohn_handler.shadowUsers(room.ID, ['chris']),
                    is_(False),
                    "No ACL Found")
        room.__acl__ = auth_acl.acl_from_aces(auth_acl.ace_allowing('sjohnson', ACT_MODERATE))
        component.provideUtility(ACLAuthorizationPolicy())
        assert_that(sjohn_handler.shadowUsers(room.ID, ['chris']), is_(True))

    @WithMockDSTrans
    def test_multiple_moderators(self):
        room, chatserver = self._create_room()
        sjohn_handler = chat.ChatHandler(chatserver, self.sessions[1])
        chris_handler = chat.ChatHandler(chatserver, self.sessions[2])
        jason_handler = chat.ChatHandler(chatserver, self.sessions[3])
        room.__acl__ = auth_acl.acl_from_aces(auth_acl.ace_allowing('sjohnson', ACT_MODERATE),
                                              auth_acl.ace_allowing('chris', ACT_MODERATE))
        component.provideUtility(ACLAuthorizationPolicy())

        assert_that(sjohn_handler.makeModerated(room.ID, True),
                    has_property('Moderated', True))
        assert_that(room.Moderators, is_(set(['sjohnson'])))

        assert_that(chris_handler.makeModerated(room.ID, True),
                    has_property('Moderated', True))
        assert_that(room.Moderators, is_(set(['sjohnson', 'chris'])))

        assert_that(jason_handler.makeModerated(room.ID, True),
                    has_property('Moderated', True))
        assert_that(room.Moderators, is_(set(['sjohnson', 'chris'])))

        assert_that(jason_handler.makeModerated(room.ID, False),
                    has_property('Moderated', True))
        assert_that(room.Moderators, is_(set(['sjohnson', 'chris'])))

        assert_that(chris_handler.makeModerated(room.ID, False),
                    has_property('Moderated', False))
        assert_that(room.Moderators, is_(()))

    @WithMockDSTrans
    def test_handler_enter_room_no_occupants_online(self):
        d = {'Occupants': [u'sjohnson', u'other'],
             'ContainerId': u'tag:nextthought.com,2011-10:x-y-z'}
        sessions = self.Sessions()
        sessions[1] = self.Session('sjohnson')
        chatserver = chat.Chatserver(sessions)
        assert_that(chat.ChatHandler(chatserver, sessions[1]).enterRoom(d),
                    is_(none()))

    @WithMockDSTrans
    def test_handler_enter_room_with_occupants_online(self):
        d = {'Occupants': [u'sjohnson', u'other'],
             'ContainerId': u'tag:nextthought.com,2011-10:x-y-z'}
        sessions = self.Sessions()
        sessions[1] = self.Session('sjohnson')
        sessions[2] = self.Session('other')
        sessions[3] = self.Session('not_occupant')
        sessions[4] = self.Session('not_occupant2')
        chatserver = chat.Chatserver(sessions,
                                     chat.TestingMappingMeetingStorage())
        handler1 = chat.ChatHandler(chatserver, sessions[1])
        handler2 = chat.ChatHandler(chatserver, sessions[2])
        handler3 = chat.ChatHandler(chatserver, sessions[3])

        meeting = handler1.enterRoom(d)
        assert_that(meeting,
                    is_(chat.Meeting))
        assert_that(meeting, has_property('creator',  'sjohnson'))
        assert_that(toExternalObject(meeting),
                    has_entry('Creator', 'sjohnson'))

        # The 'other' user should have received notification to enter the room
        def _check_other_enteredRoom_event(sid=2):
            assert_that(sessions[sid].socket.events, has_length(1))
            assert_that(sessions[sid].socket.events[0],
                        has_entry('name', 'chat_enteredRoom'))
            assert_that(sessions[sid].socket.events[0],
                        has_entry('args', has_item(has_entry('Class', 'RoomInfo'))))
            assert_that(sessions[sid].socket.events[0]['args'][0],
                        has_key('ID'))

        _check_other_enteredRoom_event()
        assert_that(auth_acl.ACLProvider(meeting),
                    permits('sjohnson', 'nti.actions.update'))
        assert_that(auth_acl.ACLProvider(meeting),
                    permits('sjohnson', 'zope.View'))

        assert_that(auth_acl.ACLProvider(meeting),
                    denies('other', 'nti.actions.update'))
        assert_that(auth_acl.ACLProvider(meeting),
                    permits('other', 'zope.View'))

        # The other user can exit this meeting...
        handler2.exitRoom(meeting.RoomId)
        assert_that(meeting.historical_occupant_names, has_item('other'))

        # ... and re-enter
        sessions.clear_all_session_events()
        assert_that(meeting, permits('other', ACT_ENTER))

        m2 = handler2.enterRoom({'RoomId': meeting.RoomId})
        assert_that(m2, is_(meeting))
        assert_that(meeting.occupant_names, has_item('other'))
        # both of them got events
        _check_other_enteredRoom_event()
        assert_that(sessions[1].socket.events[0],
                    has_entry('name', 'chat_roomMembershipChanged'))

        # Some random person cannot
        m3 = handler3.enterRoom({'RoomId': meeting.RoomId})
        assert_that(m3, is_(none()))

        # But the owner can add this random person
        sessions.clear_all_session_events()

        result = handler1.addOccupantToRoom(meeting.RoomId, 'not_occupant')
        assert_that(result, is_(chat.Meeting))
        assert_that(sessions[1].socket.events[0],
                    has_entry('name', 'chat_roomMembershipChanged'))
        assert_that(sessions[2].socket.events[0],
                    has_entry('name', 'chat_roomMembershipChanged'))
        _check_other_enteredRoom_event(3)

        # Another occupant cannot, though, due to the acl
        sessions.clear_all_session_events()
        result = handler2.addOccupantToRoom(meeting.RoomId, 'not_occupant2')
        assert_that(result, is_(none()))

        # The owner cannot add someone offline
        assert_that(handler1.addOccupantToRoom(meeting.RoomId, 'offline'),
                    is_(none()))

        # The owner cannot add someone already in/previously exited the room
        assert_that(handler1.addOccupantToRoom(meeting.RoomId, 'not_occupant'),
                    is_(none()))

    @WithMockDSTrans
    def test_integration_chat_storage_studygroup(self):
        ds = self.ds
        import nti.dataserver.meeting_container_storage as mcs

        user = User.create_user(ds, username=u'foo@bar', password=u'temp001')
        ds.root['users']['foo@bar'] = user
        ds.root['users']['friend@bar'] = User.create_user(ds, username=u'friend@bar',
                                                          password=u'temp001')
        fl1 = user.maybeCreateContainedObjectWithType('FriendsLists',
                                                      {'Username': u'fl1', 'friends': [u'friend@bar']})
        fl1.containerId = u'FriendsLists'
        fl1.creator = user
        fl1.addFriend(ds.root['users']['friend@bar'])
        user.addContainedObject(fl1)

        mc = mcs.MeetingContainerStorage(ds)
        sessions = self.Sessions()
        sessions[1] = self.Session('sjohnson')
        sessions[2] = self.Session('friend@bar')
        sessions[3] = self.Session('foo@bar')
        chatserver = chat.Chatserver(sessions, chat.TestingMappingMeetingStorage(),
                                     meeting_container_storage=mc)
        foo_handler = chat.ChatHandler(chatserver, sessions[3])
        friend_handler = chat.ChatHandler(chatserver, sessions[2])
        sj_handler = chat.ChatHandler(chatserver, sessions[1])

        # I entered and created.
        room = foo_handler.enterRoom({'ContainerId': fl1.NTIID})
        assert_that(room, is_(not_none()))
        assert_that(room, has_property('creator', 'foo@bar'))
        assert_that(room,
                    has_property('occupant_names', set((foo_handler.session.owner, 'friend@bar'))))

        # A friend can enter and be in the same room.
        assert_that(friend_handler.enterRoom({"ContainerId": fl1.NTIID}),
                    is_(room))

        # A foreigner cannot.
        assert_that(sj_handler.enterRoom({'ContainerId': fl1.NTIID}),
                    is_(none()))

        # The friend can exit and re-enter the room
        assert_that(friend_handler.exitRoom(room.ID), is_(True))
        assert_that(friend_handler.enterRoom({"ContainerId": fl1.NTIID}),
                    is_(same_instance(room)))

        # We can both exit, and now we get a new room
        assert_that(friend_handler.exitRoom(room.ID), is_(True))

        assert_that(foo_handler.exitRoom(room.ID), is_(True))

        room2 = foo_handler.enterRoom({'ContainerId': fl1.NTIID})
        assert_that(room2, is_(not_none()))
        assert_that(room2, is_(is_not(same_instance(room))))
        assert_that(friend_handler.enterRoom({"ContainerId": fl1.NTIID}),
                    is_(same_instance(room2)))

        # Now if both of those sessions go away, then
        # the old room is closed out and entering gets a new room
        del sessions[2]
        del sessions[3]
        sessions[4] = self.Session('friend@bar')
        sessions[5] = self.Session('foo@bar')
        foo_handler = chat.ChatHandler(chatserver, sessions[5])
        friend_handler = chat.ChatHandler(chatserver, sessions[4])

        room3 = foo_handler.enterRoom({'ContainerId': fl1.NTIID})
        assert_that(room3, is_(not_none()))
        assert_that(room3, is_not(same_instance(room)))
        assert_that(room3, is_not(same_instance(room2)))
        assert_that(friend_handler.enterRoom({"ContainerId": fl1.NTIID}),
                    is_(same_instance(room3)))

        # I can post a message to that room
        msg = chat.MessageInfo()
        msg.Creator = u'foo@bar'
        msg.recipients = ['friend@bar']
        msg.Body = u'This is the body'
        msg.containerId = room3.ID
        assert_that(foo_handler.postMessage(msg), is_(True))
        # But somebody else cannot
        sessions[6] = self.Session('other@other')
        other_handler = chat.ChatHandler(chatserver, sessions[6])
        msg.Creator = u'other@other'
        assert_that(other_handler.postMessage(msg), is_(False))

        # I can become the moderator of this room
        del sessions[5].socket.events[:]
        component.provideUtility(ACLAuthorizationPolicy())
        assert_that(foo_handler.makeModerated(room3.ID, True), is_(room3))
        assert_that(room3.Moderators, is_(set([foo_handler.session.owner])))
        assert_that(room3.Moderated, is_(True))
        assert_that(room3, is_(chat.ModeratedMeeting))
        assert_that(sessions[5].socket.events, has_length(2))
        assert_that(sessions[5].socket.events,
                    contains(has_entry('name', 'chat_roomModerationChanged'),
                             has_entry('name', 'chat_roomModerationChanged')))

        assert_that(auth_acl.ACLProvider(room3),
                    permits('foo@bar', 'zope.View'))
        assert_that(auth_acl.ACLProvider(room3),
                    permits('friend@bar', 'zope.View'))

    @WithMockDSTrans
    def test_msg_to_def_channel_unmod_goes_to_user_transcript(self):
        sessions = self.Sessions()
        sessions[1] = self.Session('sjohnson')
        sessions[2] = self.Session('chris')
        sessions[3] = self.Session('jason')
        chatserver = chat.Chatserver(sessions,
                                     chat.TestingMappingMeetingStorage())
        component.provideUtility(chatserver)
        room = chatserver.create_room_from_dict({'Occupants': [u'jason', u'chris', u'sjohnson'],
                                                 'Creator': u'sjohnson',
                                                 'ContainerId': u'tag:nextthought.com,2011-10:x-y-z'})
        component.getUtility(IIntIds).register(room)
        msg = chat.MessageInfo()
        msg.Creator = u'jason'
        msg.recipients = ['chris']  # But the default channel
        msg.Body = u'This is the body'
        chatserver.post_message_to_room(room.ID, msg)
        assert_that(IConnection(msg, None), is_(not_none()))

        for user in ('sjohnson', 'chris', 'jason'):
            assert_that(transcript_for_user_in_room(user, room.ID).get_message(msg.ID),
                        is_(msg))
            user = User.get_user(user)
            tx_id = _transcript_ntiid(room, user, TYPE_TRANSCRIPT)
            assert_that(find_object_with_ntiid(tx_id).get_message(msg.ID),
                        is_(msg))

    @WithMockDSTrans
    def test_msg_to_state_channel_unmod_not_in_user_transcript(self):
        sessions = self.Sessions()
        sessions[1] = self.Session('sjohnson')
        sessions[2] = self.Session('chris')
        sessions[3] = self.Session('jason')
        chatserver = chat.Chatserver(
            sessions, chat.TestingMappingMeetingStorage())
        component.provideUtility(chatserver)
        room = chatserver.create_room_from_dict({'Occupants': [u'jason', u'chris', u'sjohnson'],
                                                 'Creator': u'sjohnson',
                                                 'ContainerId': u'tag:nextthought.com,2011-10:x-y-z'})
        component.getUtility(IIntIds).register(room)

        sessions.clear_all_session_events()

        msg = chat.MessageInfo()
        msg.Creator = u'jason'
        msg.recipients = [u'chris']  # but this is ignored
        msg.channel = chat.CHANNEL_STATE
        msg.Body = {'state': u'active', 'extra_key_to_drop': True}
        chatserver.post_message_to_room(room.ID, msg)

        # The msg cannot become an IConnection, because it was never inserted into a parent tree
        # or saved
        assert_that(IConnection(msg, None), is_(none()))

        for user in ('sjohnson', 'chris', 'jason'):
            # No transcript yet
            assert_that(transcript_for_user_in_room(user, room.ID),
                        is_(none()))
            user = User.get_user(user)
            tx_id = _transcript_ntiid(room, user, TYPE_TRANSCRIPT)
            assert_that(find_object_with_ntiid(tx_id), is_(none()))

        # But all the occupants did get the message
        for session in sessions:
            assert_that(session.socket.events, has_length(1))
            event = session.socket.events[0]
            __traceback_info__ = session, event
            assert_that(event['args'],
                        has_item(has_entry('channel', chat.CHANNEL_STATE)))
            # And the body was sanitized
            assert_that(event['args'][0],
                        has_entry('body', {'state': 'active'}))

    @WithMockDSTrans
    def test_state_channel_ignored_in_moderated_room(self):
        room, chatserver = self._create_moderated_room()
        self.sessions.clear_all_session_events()

        msg = chat.MessageInfo()
        msg.channel = chat.CHANNEL_STATE
        msg.recipients = [u'chris']

        # Even from the moderator
        msg.Creator = u'sjohnson'
        # Accepted, but not sent
        assert_that(chatserver.post_message_to_room(room.ID, msg), is_(True))

        for session in self.sessions:
            assert_that(session.socket.events, has_length(0))

    @WithMockDSTrans
    def test_moderator_send_default(self):
        room, chatserver = self._create_moderated_room()

        msg = chat.MessageInfo()
        msg.channel = chat.CHANNEL_DEFAULT
        msg.recipients = [u'chris']

        # Only the moderator
        msg.Creator = u'sjohnson'
        assert_that(chatserver.post_message_to_room(room.ID, msg), is_(True))

    @WithMockDSTrans
    def test_content(self):
        room, chatserver = self._create_moderated_room()

        msg = chat.MessageInfo()
        msg.channel = chat.CHANNEL_CONTENT
        msg.recipients = [u'chris@nextthought.com']

        # Only the moderator
        msg.Creator = u'jason'  # Not the moderator
        assert_that(chatserver.post_message_to_room(room.ID, msg), is_(False))

        # Body must be a mapping with a valid NTIID
        msg.Creator = u'sjohnson'  # The moderator
        msg.sender_sid = 1
        msg.Body = {}
        assert_that(chatserver.post_message_to_room(room.ID, msg), is_(False))

        msg.Body = {'ntiid': u'foo'}
        assert_that(chatserver.post_message_to_room(room.ID, msg), is_(False))

        msg.Body = {'ntiid': ROOT}
        assert_that(chatserver.post_message_to_room(room.ID, msg), is_(True))

        # Unknown fields are sanitized
        msg.Body['Foo'] = u'bar'
        assert_that(chatserver.post_message_to_room(room.ID, msg), is_(True))
        assert_that(msg.Body, is_({'ntiid': ROOT}))

    @WithMockDSTrans
    def test_meta(self):
        room, chatserver = self._create_moderated_room()

        msg = chat.MessageInfo()
        msg.channel = chat.CHANNEL_META
        msg.recipients = ['chris']

        # Only the moderator
        msg.Creator = u'jason'
        assert_that(chatserver.post_message_to_room(room.ID, msg), is_(False))

        # Body must be a mapping with a valid channel and action
        msg.Creator = u'sjohnson'
        msg.sender_sid = 1
        msg.Body = {}
        assert_that(chatserver.post_message_to_room(room.ID, msg), is_(False))

        msg.Body = {'channel': 'foo', 'action': 'foo'}
        assert_that(chatserver.post_message_to_room(room.ID, msg), is_(False))

        msg.Body = {'channel': chat.CHANNEL_DEFAULT, 'action': 'foo'}
        assert_that(chatserver.post_message_to_room(room.ID, msg), is_(False))

        msg.Body = {'channel': chat.CHANNEL_DEFAULT,
                    'action': 'clearPinned', 'foo': 'bar'}
        assert_that(chatserver.post_message_to_room(room.ID, msg), is_(True))
        # Unknown fields are sanitized
        assert_that(msg.Body,
                    is_({'channel': chat.CHANNEL_DEFAULT, 'action': 'clearPinned'}))
        # recipients are ignored
        assert_that(msg.recipients, is_(()))

        # pinning requires valid ntiid
        msg.Body = {'channel': chat.CHANNEL_DEFAULT,
                    'action': u'pin', 'ntiid': u'bar'}
        assert_that(chatserver.post_message_to_room(room.ID, msg), is_(False))

        msg.Body = {'channel': chat.CHANNEL_DEFAULT,
                    'action': u'pin', 'ntiid': ROOT, 'foo': u'bar'}
        assert_that(chatserver.post_message_to_room(room.ID, msg), is_(True))
        # Unknown fields are sanitized
        assert_that(msg.Body,
                    is_({'channel': chat.CHANNEL_DEFAULT, 'action': 'pin', 'ntiid': ROOT}))
        # recipients are ignored
        assert_that(msg.recipients, is_(()))

    @WithMockDSTrans
    def test_poll(self):
        room, chatserver = self._create_moderated_room()

        msg = chat.MessageInfo()
        msg.channel = chat.CHANNEL_POLL
        msg.recipients = [u'chris']

        # Only the moderator
        msg.Creator = u'jason'
        assert_that(chatserver.post_message_to_room(room.ID, msg), is_(False))
        # unless its a reply
        msg_info = chat.MessageInfo()
        component.getUtility(IIntIds).register(msg_info)
        self.ds.root._p_jar.add(msg_info)
        msg.inReplyTo = msg_info
        assert_that(chatserver.post_message_to_room(room.ID, msg), is_(True))
        # only went to moderators
        assert_that(msg.recipients, is_({u'sjohnson'}))

        # The moderator sends to everyone
        msg.Creator = u'sjohnson'
        msg.sender_sid = 1
        msg.Body = {}
        msg.recipients = ()
        assert_that(chatserver.post_message_to_room(room.ID, msg), is_(True))
        assert_that(msg.recipients, is_(()))

    @WithMockDSTrans
    def test_whisper_to_shadow_goes_to_mod_transcript(self):
        room, chatserver = self._create_moderated_room()
        room.shadow_user('chris')  # whispers to chris come to sjohnson.

        msg = chat.MessageInfo()
        msg.Creator = u'jason'
        msg.recipients = ['chris']
        msg.Body = u'This is the body'
        msg.channel = chat.CHANNEL_WHISPER
        chatserver.post_message_to_room(room.ID, msg)  # jason whispers to Chris
        assert_that(msg.sharedWith, is_(set(['jason', 'chris'])))

        # It should now be in the moderator transcript
        assert_that(transcript_for_user_in_room('sjohnson', room.ID).get_message(msg.ID),
                    is_(msg))

        # Every one of them should have it in their TS
        for user in ('sjohnson', 'chris', 'jason'):
            assert_that(transcript_for_user_in_room(user, room.ID).get_message(msg.ID),
                        is_(msg))

    @WithMockDSTrans
    def test_whisper_mod_recip_one_plus_sender(self):
        room, chatserver = self._create_moderated_room()

        msg = chat.MessageInfo()
        msg.Creator = u'jason'
        msg.recipients = ['chris', 'jason']
        msg.Body = u'This is the body'
        msg.channel = chat.CHANNEL_WHISPER
        chatserver.post_message_to_room(room.ID, msg)  # jason whispers to Chris
        assert_that(msg.sharedWith, is_(set(['jason', 'chris'])))
        assert_that(auth_acl.ACLProvider(msg), permits('jason', 'zope.View'))
        assert_that(auth_acl.ACLProvider(msg), permits('chris', 'zope.View'))

        # It should not be in the moderator transcript
        assert_that(transcript_for_user_in_room('sjohnson', room.ID),
                    is_(none()))

        # Every one of them should have it in their TS
        for user in ('chris', 'jason'):
            assert_that(transcript_for_user_in_room(user, room.ID).get_message(msg.ID),
                        is_(msg))

    @WithMockDSTrans
    def test_whisper_too_many_dropped(self):
        room, chatserver = self._create_moderated_room()

        msg = chat.MessageInfo()
        msg.Creator = u'jason'
        msg.recipients = ['chris', 'jason', 'sjohnson']
        msg.Body = u'This is the body'
        msg.channel = chat.CHANNEL_WHISPER
        # jason whispers to Chris AND sjohnson
        chatserver.post_message_to_room(room.ID, msg)
        assert_that(msg.sharedWith, is_empty())

        # It should not be in anyone's transcript
        assert_that(transcript_for_user_in_room('sjohnson', room.ID),
                    is_(none()))

        # Every one of them should have it in their TS
        for user in ('chris', 'jason', 'sjohnson'):
            assert_that(transcript_for_user_in_room(user, room.ID),
                        is_(none()))

    @WithMockDSTrans
    def test_msg_only_to_self_dropped(self):
        room, chatserver = self._create_room()
        # no shadows

        msg = chat.MessageInfo()
        msg.Creator = u'jason'
        msg.recipients = ['jason']
        msg.Body = u'This is the body'
        msg.channel = chat.CHANNEL_WHISPER
        chatserver.post_message_to_room(room.ID, msg)  # jason whispers to Chris
        assert_that(msg.sharedWith, is_empty())

        # No one has it, it got dropped.
        for user in ('chris', 'jason'):
            assert_that(transcript_for_user_in_room(user, room.ID),
                        is_(none()))

    @WithMockDSTrans
    def test_simple_transcript_summary(self):
        room, chatserver = self._create_room({
            'ContainerId': u'foobar',
            'Active': False
        })
        msg = chat.MessageInfo()
        msg.Creator = u'jason'
        msg.Body = u'This is the body'
        chatserver.post_message_to_room(room.ID, msg)
        assert_that(msg.sharedWith, is_(set(['jason', 'chris', 'sjohnson'])))

        for user in ('sjohnson', 'chris', 'jason'):
            summaries = list_transcripts_for_user(user)
            assert_that(summaries, has_length(1))
            summary = summaries[0]
            assert_that(summary.RoomInfo, is_(room))
            assert_that(summary.NTIID, is_(not_none()))
            assert_that(transcript_summaries_for_user_in_container(user, 'foobar'),
                        has_key(room.ID))
            assert_that(summary.Contributors,
                        is_(set(['jason', 'chris', 'sjohnson'])))

    @WithMockDSTrans
    def test_transcript_summary_for_room_has_ntiid(self):
        from zope import dottedname
        clazz = 'nti.dataserver.meeting_storage.CreatorBasedAnnotationMeetingStorage'
        user_meeting_storage = dottedname.resolve.resolve(clazz)
        room, chatserver = self._create_room({
            'ContainerId': u'tag:nextthought.com,2011-11:OU-MeetingRoom-CS101.1',
            'Active': False
        },
            meeting_storage_factory=user_meeting_storage)
        assert_that(room.containerId, is_(not_none()))
        msg = chat.MessageInfo()
        msg.Creator = u'jason'
        msg.Body = u'This is the body'
        chatserver.post_message_to_room(room.ID, msg)
        assert_that(msg.sharedWith, is_(set(['jason', 'chris', 'sjohnson'])))

        for user in ('sjohnson', 'chris', 'jason'):
            summaries = list_transcripts_for_user(user)
            assert_that(summaries, has_length(1))
            summary = summaries[0]
            assert_that(summary.RoomInfo, is_(room))
            assert_that(get_type(summary.NTIID), is_(TYPE_TRANSCRIPT_SUMMARY))
            assert_that(transcript_summaries_for_user_in_container(user, room.containerId),
                        has_key(room.ID))
            assert_that(summary.Contributors,
                        is_(set(['jason', 'chris', 'sjohnson'])))
            # Links
            assert_that(summary.links, has_length(1))
            assert_that(summary.links[0].target, provides(ITranscript))

            current_mock_ds = mock_dataserver.current_mock_ds
            assert_that(current_mock_ds.get_by_oid(room.id, ignore_creator=True),
                        not_none())
            user = User.get_user(user)
            transcript = find_object_with_ntiid(make_ntiid(
                base=summary.NTIID, nttype=TYPE_TRANSCRIPT))
            assert_that(transcript, provides(ITranscript))

    @WithMockDSTrans
    def test_transcript_replyto_offline(self):
        # With only two of us online, a reply to a note
        # shared with all three is transcripted to all three
        sessions = self.Sessions()
        sessions[1] = self.Session('sjohnson')
        sessions[3] = self.Session('jason')
        # Create a user, but remove the session
        sessions[2] = self.Session('chris')
        chris_user = sessions[2].the_user
        del sessions[2]
        chatserver = chat.Chatserver(sessions,
                                     chat.TestingMappingMeetingStorage())

        conn = mock_dataserver.current_transaction
        component.provideUtility(chatserver)

        n = Note()
        n.addSharingTarget(sessions[1].the_user)
        n.addSharingTarget(sessions[3].the_user)
        n.addSharingTarget(chris_user)
        assert_that(n.flattenedSharingTargetNames,
                    is_(set(['jason', 'chris', 'sjohnson'])))
        conn.add(n)
        component.getUtility(IIntIds).register(n)
        conn.root()['Note'] = n
        n_oid = toExternalOID(n)

        room = chatserver.create_room_from_dict({'Occupants': [u'jason', u'sjohnson'],
                                                 'ContainerId': u'foobar',
                                                 'inReplyTo': n_oid,
                                                 'Creator': u'sjohnson',
                                                 'Active': False})
        msg = chat.MessageInfo()
        msg.Creator = u'jason'
        msg.Body = u'This is the body'
        chatserver.post_message_to_room(room.ID, msg)
        assert_that(msg.sharedWith, is_(set(['jason', 'chris', 'sjohnson'])))

        for user in ('sjohnson', 'chris', 'jason'):
            summaries = list_transcripts_for_user(user)
            assert_that(summaries, has_length(1))
            summary = summaries[0]
            assert_that(summary.RoomInfo, is_(room))
            assert_that(transcript_summaries_for_user_in_container(user, 'foobar'),
                        has_key(room.ID))
        assert_that(summary.Contributors,
                    is_(set(['jason', 'chris', 'sjohnson'])))

    @WithMockDSTrans
    def test_chat_handler_adapter(self):
        sessions = self.Sessions()
        sessions[1] = self.Session('sjohnson')
        socket = sessions[1]

        @interface.implementer(IChatserver)
        class CServer(object):
            pass
        cserver = CServer()
        component.provideUtility(cserver)

        subs = component.subscribers((socket,), ISocketEventHandler)
        assert_that(subs, has_item(is_(chat.ChatHandler)))

    @WithMockDSTrans
    def test_send_event_to_user_non_external_errors(self):
        sessions = self.Sessions()
        sessions[1] = self.Session('sjohnson')
        chatserver = chat.Chatserver(sessions)

        # Top-level
        with self.assertRaises(NonExternalizableObjectError):
            chatserver.send_event_to_user('sjohnson', 'event', object())

        # Nested
        with self.assertRaises(NonExternalizableObjectError):
            chatserver.send_event_to_user('sjohnson', 'event', [object()])

    @WithMockDSTrans
    def test_send_event_to_user_links(self):
        sessions = self.Sessions()
        sessions[1] = self.Session('sjohnson', strict_events=True)
        chatserver = chat.Chatserver(sessions)

        link = Link('/foo', rel=u'favorite')
        # Top-level works
        chatserver.send_event_to_user('sjohnson', 'event', link)
        assert_that(sessions[1].socket.events, has_length(1))

        sessions.clear_all_session_events()
        # Nested works, though
        chatserver.send_event_to_user('sjohnson', 'event', [link])
        assert_that(sessions[1].socket.events, has_length(1))

    @WithMockDSTrans
    def test_handler_setPresence(self):
        sessions = self.Sessions()
        sessions[1] = self.Session('sjohnson')
        chatserver = chat.Chatserver(sessions,
                                     chat.TestingMappingMeetingStorage())
        handler1 = chat.ChatHandler(chatserver, sessions[1])

        presence = PresenceInfo(type=u'available', show=u'dnd')
        res = handler1.setPresence(presence)
        assert_that(res, is_true())
        assert_that(sessions[1].socket.events, has_length(2))

        echo_me = sessions[1].socket.events[0]
        my_contacts = sessions[1].socket.events[1]

        assert_that(echo_me, has_entry('name', 'chat_setPresenceOfUsersTo'))
        assert_that(echo_me['args'],
                    has_item(has_entry('sjohnson',
                                       has_entries('show', 'dnd', 'type', 'available', 'username', 'sjohnson'))))

        # I have no contact subscriptions
        assert_that(my_contacts,
                    has_entry('name', 'chat_setPresenceOfUsersTo'))
        assert_that(my_contacts['args'], has_length(1))
        assert_that(my_contacts['args'][0], is_({}))

        # But I can add some
        sessions[2] = self.Session('otheruser')
        handler2 = chat.ChatHandler(chatserver, sessions[2])
        sessions[1].the_user.follow(sessions[2].the_user)
        handler2.setPresence(PresenceInfo(type=u'available',
                                          status=IPlainTextContentFragment(u'Hi')))
        sessions.clear_all_session_events()

        presence = PresenceInfo(type=u'available', show=u'xa')
        handler1.setPresence(presence)

        my_contacts = sessions[1].socket.events[1]

        assert_that(my_contacts,
                    has_entry('name', 'chat_setPresenceOfUsersTo'))
        assert_that(my_contacts['args'], has_length(1))
        assert_that(my_contacts['args'][0],
                    has_entry('otheruser', has_entries('type', 'available', 'status', 'Hi')))

        # If there is no presence info for the other user,
        # we get no info about him, thus we are to assume he is in the default
        # offline state
        sessions.clear_all_session_events()
        chatserver.removePresenceOfUser('otheruser')
        handler1.setPresence(presence)

        my_contacts = sessions[1].socket.events[1]
        assert_that(my_contacts,
                    has_entry('name', 'chat_setPresenceOfUsersTo'))
        assert_that(my_contacts['args'], has_length(1))
        assert_that(my_contacts['args'][0], is_empty())


class TestFunctionalChatserver(ApplicationLayerTest, _ChatserverTestMixin):

    @WithSharedApplicationMockDS
    def test_send_event_to_users_correct_edit_links_Pyramid_functional(self):
        #"An Edit link is only sent to users that have write permissions."
        # This is a high-level test involving the appserver as well
        with mock_dataserver.mock_db_trans(self.ds):
            auth_policy = component.getUtility(IAuthenticationPolicy)
            with auth_policy.impersonating_userid('sjohnson')():

                sessions = self.Sessions()
                sessions[1] = self.Session('sjohnson', strict_events=True)
                sessions[2] = self.Session('jason', strict_events=True)
                chatserver = chat.Chatserver(sessions)

                creator = sessions[1].the_user
                note = Note()
                note.creator = creator
                note.addSharingTarget(sessions[2].the_user)
                self.ds.root._p_jar.add(note)
                # If there's no __parent__, there's no link
                note.__parent__ = self.ds.root
                note.__name__ = u'himitsu'

                # Check the permissions
                assert_that(note, permits('sjohnson', auth.ACT_READ))
                assert_that(note, permits('sjohnson', auth.ACT_UPDATE))
                assert_that(note, denies('jason', auth.ACT_UPDATE))
                assert_that(note, permits('jason', auth.ACT_READ))

                # Broadcast the event to the owner
                chatserver.send_event_to_user('sjohnson', 'event', note)
                assert_that(sessions[1].socket.events, has_length(1))
                note_to_owner = sessions[1].socket.events[0]['args'][0]
                assert_that(note_to_owner,
                            has_entry('Links', has_item(has_entry('rel', 'edit'))))

                # Broadcast the event to the shared with
                chatserver.send_event_to_user('jason', 'event', note)
                assert_that(sessions[2].socket.events, has_length(1))
                note_to_shared = sessions[2].socket.events[0]['args'][0]
                __traceback_info__ = note_to_shared.get('Links')
                assert_that(note_to_shared,
                            has_entry('Links', is_not(has_item(has_entry('rel', 'edit')))))
                assert_that(note_to_shared, is_not(note_to_owner))

                msg_info = chat.MessageInfo()
                msg_info.creator = sessions[1].the_user.username
                msg_info.recipients = [sessions[2].the_user.username]
                msg_info.sharedWith = msg_info.recipients
                msg_info.containerId = u'foobar'
                # Make sure it has a parent and oid
                storage = IMessageInfoStorage(msg_info)
                storage.add_message(msg_info)

                assert_that(msg_info, permits('sjohnson', auth.ACT_UPDATE))
                assert_that(msg_info, denies('jason', auth.ACT_UPDATE))
                assert_that(msg_info, permits('jason', auth.ACT_READ))

                del sessions[2].socket.events[:]
                chatserver.send_event_to_user('jason', 'event', msg_info)
                assert_that(sessions[2].socket.events, has_length(1))
                ext_msg = sessions[2].socket.events[0]['args'][0]
                assert_that(ext_msg,
                            has_entry('Links', has_item(has_entry('rel', 'flag'))))
