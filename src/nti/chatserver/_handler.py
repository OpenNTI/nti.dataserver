#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Chatserver functionality.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import os
import six
import time
import warnings

from zope import component
from zope import interface

from zope.annotation import factory as an_factory

from zope.cachedescriptors.property import Lazy

from zope.event import notify

from zope.interface.common.mapping import IFullMapping

from persistent import Persistent

from persistent.mapping import PersistentMapping

from nti.chatserver import MessageFactory as _

from nti.chatserver._metaclass import _ChatObjectMeta

from nti.chatserver.interfaces import ACT_MODERATE

from nti.chatserver.interfaces import IContacts
from nti.chatserver.interfaces import IChatserver
from nti.chatserver.interfaces import IPresenceInfo
from nti.chatserver.interfaces import IChatEventHandler
from nti.chatserver.interfaces import UserExitRoomEvent
from nti.chatserver.interfaces import UserEnterRoomEvent

from nti.common.sets import discard as _discard

# FIXME: Break this dependency
from nti.dataserver import authorization_acl as auth_acl

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import ICoppaUserWithoutAgreement

from nti.dataserver.users.users import User

from nti.externalization.interfaces import StandardExternalFields as XFields

from nti.schema.field import Object

from nti.socketio.interfaces import ISocketSession
from nti.socketio.interfaces import ISocketEventHandler
from nti.socketio.interfaces import SocketEventHandlerClientError

from nti.zodb.interfaces import ITokenBucket
from nti.zodb.tokenbucket import PersistentTokenBucket

EVT_EXITED_ROOM = 'chat_exitedRoom'
EVT_POST_MESSOGE = 'chat_postMessage'
EVT_RECV_MESSAGE = 'chat_recvMessage'
EVT_ENTERED_ROOM = 'chat_enteredRoom'

logger = __import__('logging').getLogger(__name__)


class MessageRateExceeded(SocketEventHandlerClientError):
    """
    Raised when a user is attempting to post too many chat messages too quickly.
    """

    i18n_message = _(u"You are trying to send too many chat messages too quickly. Please wait and try again.")


class IChatHandlerSessionState(interface.Interface):

    rooms_i_moderate = Object(IFullMapping,
                              title=u"Mapping of rooms I moderate")

    message_post_rate_limit = Object(ITokenBucket,
                                     title=u"Take one token for every message you attempt to post.")


@interface.implementer(IChatHandlerSessionState)
@component.adapter(ISocketSession)
class _ChatHandlerSessionState(Persistent):
    """
    An annotation for sessions to store the state a chat handler likes to have,
    since chat handlers have no state for longer than a single event.

    .. caution:: Recall that relatively speaking annotations are expensive and probably
            not suited to writing something for every incoming message (that creates
            lots of database transaction traffic) such as would potentially be needed
            for persistent rate-based throttling. On the other hand, if you're going to be
            writing something anyway (e.g., you have successfully posted a message to a chat
            room) then adding something here is probably not a problem.
    """

    @Lazy
    def rooms_i_moderate(self):
        return PersistentMapping()

    @Lazy
    def message_post_rate_limit(self):
        # This is sure to be heavily tweaked over time. Initially, we
        # start with one limit for all users: In any given 60 second period,
        # you can post 30 messages (one every other second). You can burst
        # faster than that, up to a max of 30 incoming messages. If you aren't
        # ever idle, you can sustain a rate of one message every two seconds.
        return PersistentTokenBucket(30, 2.0)

_ChatHandlerSessionStateFactory = an_factory(_ChatHandlerSessionState)


@six.add_metaclass(_ChatObjectMeta)
@interface.implementer(IChatEventHandler)
@component.adapter(IUser, ISocketSession, IChatserver)
class _ChatHandler(object):
    """
    Class to handle each of the messages sent to or from a client in the ``chat`` prefix.

    As a socket event handler, instances of this class are created
    fresh to handle every event and thus have no persistent state. This
    objects uses the strategy of adapting the session to storage using
    annotations if necessary to store additional state.
    """

    __emits__ = ('recvMessageForAttention', 'presenceOfUserChangedTo',
                 'data_noticeIncomingChange', 'failedToEnterRoom',
                 'setPresenceOfUsersTo')

    event_prefix = 'chat'  #: the namespace of events we handle

    session = None
    chatserver = None
    session_user = None

    # recall that public methods correspond to incomming events

    def __init__(self, *args):
        # For backwards compat, we accept either two args or three, as specified
        # in our adapter contract
        if len(args) == 3:
            self.session_user = args[0]
            self.session = args[1]
            self.chatserver = args[2]
        else:
            assert len(args) == 2
            self.chatserver = args[0]
            self.session = args[1]
            self.session_user = User.get_user(self.session.owner)

    def __reduce__(self):
        raise TypeError()

    def __str__(self):
        return "%s(%s %s)" % (self.__class__.__name__,
                              self.session.owner,
                              self.session.session_id)

    def _get_chatserver(self):
        return self.chatserver or component.queryUtility(IChatserver)

    def _set_chatserver(self, cs):
        self.chatserver = cs
    _chatserver = property(_get_chatserver, _set_chatserver)

    def postMessage(self, msg_info):
        # Ensure that the sender correctly matches.
        msg_info.Sender = self.session.owner
        msg_info.sender_sid = self.session.session_id
        result = True
        # Rate limit *all* incoming chat messages
        state = IChatHandlerSessionState(self.session)
        if not state.message_post_rate_limit.consume():
            if 'DATASERVER_SYNC_CHANGES' in os.environ:  # hack for testing
                logger.warn("Allowing message rate for %s to exceed throttle %s during integration testings.",
                            self, state.message_post_rate_limit)
            else:
                raise MessageRateExceeded()

        for room in set(msg_info.rooms):
            result &= self._chatserver.post_message_to_room(room, msg_info)
        return result

    def enterRoom(self, room_info):
        room = None

        if room_info.get('RoomId') is not None:
            # Trying to join an established room
            # Can only do this if the meeting currently exists and we were once
            # a part of it
            room = self._chatserver.enter_existing_meeting(room_info, 
                                                           self.session.owner)
        elif len(room_info.get('Occupants', ())) == 0 and XFields.CONTAINER_ID in room_info:
            # No occupants, but a container ID. This must be for something
            # that can persistently host meetings. We want
            # to either create or join it.
            room_info['Creator'] = self.session.owner
            room_info['Occupants'] = [
                (self.session.owner, self.session.session_id)
            ]
            room = self._chatserver.enter_meeting_in_container(room_info)
        else:
            # Creating a room to chat with. Make sure I'm in it.
            # More than that, make sure it's my session, and any
            # of my friends lists are expanded. Make sure it has an active
            # occupant besides me
            room_info['Creator'] = self.session.owner
            _discard(room_info.get('Occupants'), self.session.owner)
            room_info['Occupants'] = list(room_info['Occupants'])
            user = self.session_user
            if user:
                for i in list(room_info['Occupants'] or ()):
                    if i in user.friendsLists:
                        room_info['Occupants'] += [x.username for x in user.friendsLists[i]]
            room_info['Occupants'].append((self.session.owner, self.session.session_id))

            def sessions_validator(sessions):
                """
                We can only create the ad-hoc room if there is another online occupant.
                """
                return len(sessions) > 1
            room = self._chatserver.create_room_from_dict(room_info,
                                                          sessions_validator=sessions_validator)

        if not room:
            self.emit_failedToEnterRoom(self.session.owner, room_info)
        else:
            notify(UserEnterRoomEvent(self.session.owner, room.id))
        return room

    def exitRoom(self, room_id):
        result = self._chatserver.exit_meeting(room_id, self.session.owner)
        if result:
            notify(UserExitRoomEvent(self.session.owner, room_id))
        return result

    def addOccupantToRoom(self, room_id, occupant_name):
        return self._chatserver.add_occupant_to_existing_meeting(room_id,
                                                                 self.session.owner,
                                                                 occupant_name)

    def makeModerated(self, room_id, flag):

        room = self._chatserver.get_meeting(room_id)
        can_moderate = auth_acl.has_permission(ACT_MODERATE,
                                               room,
                                               self.session.owner)
        if not can_moderate:
            logger.debug("%s not allowed to moderate room %s: %s",
                         self, room, can_moderate)
            return room

        if flag:
            if flag != room.Moderated:
                room.Moderated = flag
            logger.debug("%s becoming a moderator of room %s", self, room)
            room.add_moderator(self.session.owner)
            IChatHandlerSessionState(self.session).rooms_i_moderate[room.RoomId] = room
        else:
            # deactivating moderation for the room
            # TODO: We need to 'pop' rooms_i_moderate in all the other handlers.
            # Thats only a minor problem, though
            if flag != room.Moderated:
                logger.debug("%s deactivating moderation of %s", self, room)
                room.Moderated = flag
            IChatHandlerSessionState(self.session).rooms_i_moderate.pop(room.RoomId, None)
        return room

    def approveMessages(self, m_ids):
        for m in m_ids:
            for room in IChatHandlerSessionState(self.session).rooms_i_moderate.itervalues():
                room.approve_message(m)

    def flagMessagesToUsers(self, m_ids, usernames):
        # TODO: Roles again. Who can flag to whom?
        warnings.warn("Allowing anyone to flag messages to users.")
        warnings.warn("Assuming that clients have seen messages flagged to them.")
        for m in m_ids:
            # TODO: Where does this state belong? Who
            # keeps the message? Passing just the ID assumes
            # that the client can find the message by id.
            self.emit_recvMessageForAttention(usernames, m)
        return True

    def shadowUsers(self, room_id, usernames):
        room = self._chatserver.get_meeting(room_id)
        can_moderate = auth_acl.has_permission(ACT_MODERATE,
                                               room,
                                               self.session.owner)
        if not can_moderate:
            logger.debug("%s not allowed to shadow in room %s: %s",
                         self, room, can_moderate)
            return False

        result = False
        if room and room.Moderated:
            result = True
            for user in usernames:
                result &= room.shadow_user(user)
        return result

    def setPresence(self, presenceinfo):
        if not IPresenceInfo.providedBy(presenceinfo):
            return False

        # canonicalize the presence username
        presenceinfo.username = self.session.owner
        # canonicalize the timestamps
        presenceinfo.lastModified = time.time()

        chatserver = self._chatserver

        # 1. Store the presence
        chatserver.setPresence(presenceinfo)

        # 2. Broadcast the presence to contacts
        contacts = IContacts(self.session_user)
        updates_to = contacts.contactNamesSubscribedToMyPresenceUpdates
        args = {self.session_user.username: presenceinfo}
        self.emit_setPresenceOfUsersTo(updates_to, args)

        # 3. Also broadcast to all my sessions
        self.emit_setPresenceOfUsersTo(self.session_user.username, args)

        # 4. Collect and broadcast my subscriptions to me.
        # NOTE: Ideally, we would do this only on "initial presence." But in the
        # event of multiple sessions for my user, "initial presence" is hard to determine
        # (e.g., we may have been 'online' at home, and when we sign in at school we go 'online' there;
        # but the overall presence didn't change. If we don't send these events now,
        # the sign-in-at-school won't know about any state. We do limit the flood rate
        # by sending just to this specific session.)
        # TODO: If the chatserver has no presence info for a user, we get nothing
        # back, and thus provide no entry in our return value. The client SHOULD be treating
        # that as unavailable, but it is possible to distinguish the two states of default-unavailable
        # and explicit-unavailable. Is that a problem? Should we thus synthesize a fake
        # entry? (What does XMPP do?)
        if presenceinfo.isAvailable():
            presences = chatserver.getPresenceOfUsers(contacts.contactNamesISubscribeToPresenceUpdates)
            args = {info.username: info for info in presences}
            self.emit_setPresenceOfUsersTo(self.session, args)
        return True


@interface.implementer(IChatEventHandler)
@component.adapter(ICoppaUserWithoutAgreement,
                   ISocketSession,
                   IChatserver)
def ChatHandlerNotAvailable(*unused_args):
    """
    A factory that produces ``None``, effectively disabling chat.
    """
    return None


@interface.implementer(ISocketEventHandler)
def ChatHandlerFactory(socketio_protocol, chatserver=None):
    session = socketio_protocol.session if hasattr(
        socketio_protocol, 'session') else socketio_protocol
    if session:
        chatserver = component.queryUtility(IChatserver) if not chatserver else chatserver
        user = User.get_user(session.owner)
    if session and chatserver and user:
        handler = component.queryMultiAdapter((user, session, chatserver),
                                              IChatEventHandler)
        return handler
    logger.warning("No session (%s) or chatserver (%s) or user (%r=%s); could not create event handler.",
                   session, chatserver, getattr(session, 'owner', None), user)
