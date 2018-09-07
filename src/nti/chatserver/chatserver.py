#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Chatserver functionality.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import uuid
import datetime

from six.moves import cPickle as pickle

from zope import component
from zope import interface

from zope.cachedescriptors.property import Lazy

from zope.deprecation import deprecated

from zope.intid.interfaces import IIntIds

from persistent.mapping import PersistentMapping

from nti.chatserver.interfaces import ACT_ENTER
from nti.chatserver.interfaces import ACT_ADD_OCCUPANT

from nti.chatserver.interfaces import IMeeting
from nti.chatserver.interfaces import IChatserver
from nti.chatserver.interfaces import IMeetingStorage

from nti.chatserver.meeting import _Meeting

from nti.dataserver.authentication import effective_principals

from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IRedisClient
from nti.dataserver.interfaces import IAuthorizationPolicy

from nti.externalization.interfaces import StandardExternalFields as XFields

from nti.externalization.internalization import update_from_external_object

from nti.externalization.persistence import NoPickle 

from nti.ntiids.ntiids import TYPE_UUID
from nti.ntiids.ntiids import make_ntiid

####
# A note on the object model:
# The concept of a meeting room is something that can contain resources.
# Meeting rooms hold meetings (at most one meeting at a time). The meetings
# are transcripted and this transcript is attached as a resource to the room.
# A meeting's ContainerID is the ID of the room. Within a meeting, a MessageInfo's
# ContainerID is the ID of the meeting.
# Some meetings take place "in the hallway" or "around the cooler" and
# as such belong to no room. When they finish, the transcript is
# accessible just to the users that participated. (These meetings
# may still have ContainerIDs of other content, and they will be accessible
# from that location, as is anything contained there.)
####

EVT_EXITED_ROOM = 'chat_exitedRoom'
EVT_POST_MESSOGE = 'chat_postMessage'
EVT_RECV_MESSAGE = 'chat_recvMessage'
EVT_ENTERED_ROOM = 'chat_enteredRoom'

logger = __import__('logging').getLogger(__name__)


@interface.implementer(IMeetingStorage)
class TestingMappingMeetingStorage(object):
    """
    An implementation of :class:`chat_interfaces.IMeetingStorage` suitable
    for use in transient, testing scenarios.
    """

    def __init__(self):
        self.meetings = dict()

    def __delitem__(self, room_id):
        del self.meetings[room_id]

    def __getitem__(self, room_id):
        return self.meetings[room_id]

    def add_room(self, room):
        assert IMeeting.providedBy(room)
        room.id = make_ntiid(provider=room.creator,
                             nttype=TYPE_UUID,
                             specific=uuid.uuid4().hex)
        ids = component.queryUtility(IIntIds)
        if ids is not None:
            ids.register(room)
        self.meetings[room.id] = room

    def get(self, room_id):
        obj = self.meetings.get(room_id)
        if IMeeting.providedBy(obj):
            return obj


_PRESENCE_TTL = datetime.timedelta(days=14)


@NoPickle
@interface.implementer(IChatserver)
class Chatserver(object):
    """ 
    Collection of all the state related to the chatserver, including active rooms, etc. 
    """

    def __init__(self,
                 user_sessions,
                 meeting_storage=None,
                 meeting_container_storage=None):
        """
        Create a chatserver.

        :param user_sessions: Supports :meth:`get_session` for session_id and :meth:`get_sessions_by_owner` for
                getting all sessions for a given user. A session has a `protocol_handler` attribute
                which has a `send_event` method.
        :param meeting_storage: Storage for meeting instances.
        :type meeting_storage: :class:`nti.chatserver.interfaces.IMeetingStorage`
        :param dict meeting_container_storage: Read-only dictionary used to look up containers
                of meetings. If the result is a :class:`IMeetingContainer`, it will be called to create the room.

        """
        super(Chatserver, self).__init__()
        self.sessions = user_sessions
        # Mapping from room id to room.
        self.rooms = meeting_storage
        if meeting_container_storage is not None:
            self.meeting_container_storage = meeting_container_storage
        else:
            self.meeting_container_storage = PersistentMapping()

    # Sessions

    def get_session_for(self, *args, **kwargs):
        return self.sessions.get_session_by_owner(*args, **kwargs)

    @Lazy
    def _redis(self):
        redis = component.getUtility(IRedisClient)
        logger.info("Using redis for presence storage")
        return redis

    # We store presence data in redis. We do not wrap a transaction around it, nor do we
    # compress it. We do want it to expire at some point in the (distant) future in case
    # of deleting users, etc. We store it as a pickle for speed. TODO: We may want to cache
    # the objects locally?

    def getPresenceOfUsers(self, usernames):
        # This implementation does not return a presence for users that are
        # unavailable because they have never set a presence, or their last
        # time seen was too long ago
        if usernames:
            keys = [
                'users/' + username + '/presence' for username in usernames
            ] 
        else:
            keys = None
        if keys:
            # pylint: disable=no-member
            presence_pickles = self._redis.mget(keys)
            presences = [
                pickle.loads(p) for p in presence_pickles if p is not None
            ]
        else:
            presences = ()
        return presences

    def setPresence(self, presence):
        # pylint: disable=no-member
        presence_ext = pickle.dumps(presence, pickle.HIGHEST_PROTOCOL)
        return self._redis.setex('users/' + presence.username + '/presence',
                                 # Recall that the timeout argument comes before
                                 # the value argument with StrictRedis, matching
                                 # the redis protocol
                                 _PRESENCE_TTL,
                                 presence_ext)

    def removePresenceOfUser(self, username):
        # pylint: disable=no-member
        return self._redis.delete('users/' + username + '/presence')

    # Low-level IO

    def send_event_to_user(self, *args):
        self.sessions.send_event_to_user(*args)

    # Rooms

    def post_message_to_room(self, room_id, msg_info):
        room = self.rooms.get(room_id)
        if room is None or not room.Active:
            logger.info("Dropping message to non-existant/inactive room '%s' '%s'", 
                        room_id, room)
            return False
        # Right now, there is no valid use case for the sender to
        # send a message only to himself. Right now, there's also
        # not a good way to signal this as an error so we silently drop it
        if len(msg_info.recipients) == 1 and not msg_info.recipients_without_sender:
            logger.info("Dropping message only to the sender in room %s", room)
            return False
        # To post a message to a room, you must be an occupant
        if msg_info.Sender not in room.occupant_session_names:
            logger.info("Dropping message from an occupant not in the room %s %s", 
                        room, msg_info)
            return False
        return room.post_message(msg_info)

    def enter_meeting_in_container(self, room_info_dict):
        """
        :param dict room_info_dict: A dict similar to the one given to :meth:`create_room_from_dict`.
                MUST have a ContainerID, which resolves to an :class:IMeetingContainer. Must
                have one value in the sequence for the Occupants key, the tuple of (sender,sid).
        :return: The room entered, or None.
        """
        # !!! This is racy.
        container = self.meeting_container_storage.get(room_info_dict[XFields.CONTAINER_ID])
        if not hasattr(container, 'enter_active_meeting'):
            # The container didn't match any storage.
            logger.info("The requested container (%s) (info: %s) is not a persistent meeting room; not entering",
                        container, room_info_dict)
            return None

        # At this point, we know we have exactly one Occupant, the (sender,sid).
        # This next call MIGHT change that, so preserve it.
        occupant_tuple = room_info_dict['Occupants'][0]
        room = container.enter_active_meeting(self, room_info_dict)
        # NOTE: The below FIXME are probably invalid, now that we are strictly name based,
        # and all sessions are equivalent. The 'semi-fix' is no longed needed
        # FIXME: If the room is never completely exited, then it may persist
        # as Active for a long time. Then users could be re-entering it
        # many, many times, leading to an ever-growing list of active sessions
        # in the room. These would never get cleaned up since once quite, they
        # could never exit the room.
        # We implement a lazy semi-fix below, by looking to see if the occupant_sessions
        # for a room has become empty. If so, then we act as if every old occupant
        # exited the room, which should result in the room no longer being active and
        # a new room being created.
        # FIXME: Clearing out all these sessions as a group means we
        # don't do any cleanout as long as there's at least one active session.
        # We need to do something better with individual cleanups.

        if room:
            logger.debug("%s entering existing persistent meeting %s",
                         occupant_tuple, room)
            # Yes, we got in. Announce this.
            room.add_occupant_name(occupant_tuple[0])
        else:
            # We didn't get in. We know we have a container, though,
            # so see if we can start one.
            logger.debug("%s creating new persistent meeting %s",
                         occupant_tuple, room_info_dict)
            room = self.create_room_from_dict(room_info_dict)
        return room

    def create_room_from_dict(self, room_info_dict, sessions_validator=None):
        """
        Creates a room given a dictionary of values.

        :param dict room_info_dict: Contains at least an `Occupants` key. This key
                is an iterable of usernames or (username,session_id) tuples.
        :param function sessions_validator: If given, a callable of one argument, a sequence of sessions.
                Returns whether or not to allow the room creation given those sessions.
        """

        room_info_dict = dict(room_info_dict)  # copy because we will modify

        # We need to resolve names into sessions, whether or not there
        # is a container, so we do it now.

        room = None
        # If the container is specified, and is found as something
        # that wants to have a say, let it.
        if XFields.CONTAINER_ID in room_info_dict:
            containerId = room_info_dict[XFields.CONTAINER_ID]
            container = self.meeting_container_storage.get(containerId)
            if hasattr(container, 'create_or_enter_meeting'):
                # The container will decide what to do with things like
                # Occupants, they may ignore it or replace it entirely.
                orig_occupants = list(room_info_dict['Occupants'] or ())
                room, created = container.create_or_enter_meeting(self, room_info_dict, 
                                                                  lambda: _Meeting(self))
                if room is None or not room.Active:
                    logger.debug("Container %s vetoed creation of room %s (%s)",
                                 container, room, room_info_dict)
                    # The container vetoed creation for some reason.
                    return None
                if room is not None and not created:
                    # We got back an already active room that we should enter.
                    # Check for our session and make sure we're in the room
                    # (just like enter_meeting_in_container)
                    logger.debug('Container %s found an existing room %s and forced us into it %s',
                                 container, room, room_info_dict)
                    for orig_occupant in orig_occupants:
                        if isinstance(orig_occupant, tuple) and orig_occupant[0] == room_info_dict['Creator']:
                            room.add_occupant_name(orig_occupant[0])
                            break
                    return room

                # Containers deal with, roughly, persistent rooms. Therefore, if they
                # give us a list of occupants, then regardless of whether
                # they are currently online these occupants should get
                # transcripts.
                for occupant in room_info_dict['Occupants'] or ():
                    if isinstance(occupant, tuple):
                        occupant = occupant[0]
                    room.add_additional_transcript_username(occupant)

        if room is None:
            room = _Meeting(self)

        # Resolve occupants, chiefly to make sure some are online
        sessions = []
        occupants = []
        for occupant in room_info_dict['Occupants'] or ():
            session = None
            session_ids = None
            if isinstance(occupant, tuple):
                # Two-tuples give us the session ID that we must find
                session_ids = occupant[1]
                occupant = occupant[0]

            session = self.get_session_for(occupant, session_ids)
            if session:
                # Only if we find a session does the occupant stay in. This
                # takes care of weird things like trying to add a Community
                # to the list.
                # TODO: This has gone back and forth. Should we still add
                # occupants to the additional_transcript_username list even if
                # they're not online (for awhile that was effectively the case)?
                # Just if they are an IUser?
                occupants.append(occupant)
                sessions.append(session.session_id)

        if not sessions or (callable(sessions_validator) and not sessions_validator(sessions)):
            logger.debug("No occupants found for room %s", room_info_dict)
            return None

        # Run it through the usual dict-to-object mechanism
        # so that we get correct OID resolution
        room_info_dict.pop('Occupants')
        room_info_dict.pop('Active', None)
        ds = component.getUtility(IDataserver)
        update_from_external_object(room, room_info_dict, context=ds)
        # Make sure the room is all setup before
        # we add the sessions, since that will broadcast
        # events using the room's info
        room.Active = True
        if not room.creator:  # The storage may have set this already, don't override
            room.creator = room_info_dict['Creator']

        # Must be stored to get an ID assigned
        self.rooms.add_room(room)
        # Now broadcast the room to the occupants
        room.add_occupant_names(occupants)
        logger.debug("Room, %s, created with %d occupant(s).",
                     room.id, len(room.occupant_names))

        return room

    def enter_existing_meeting(self, room_info, occupant_name):
        room_info_dict = dict(room_info)  # in case we modify
        room_id = room_info_dict['RoomId']

        room = self.get_meeting(room_id)
        if not room or not room.Active:
            logger.debug("%s not re-entering inactive/gone room %s/%s",
                         occupant_name, room, room_id)
            return None

        # TODO: We could centralize this type of checking with a convenience
        # utility somewhere.
        authorization_policy = component.queryUtility(IAuthorizationPolicy)
        if     authorization_policy is None \
            or authorization_policy.permits(room, effective_principals(occupant_name), ACT_ENTER):
            # Yes, we can enter
            logger.debug("%s re-entering room %s/%s due to auth policy %s",
                         occupant_name, room, room_id, authorization_policy)
            # broadcast the enter room event
            room.add_occupant_name(occupant_name)
            return room

        # otherwise, return none

    def add_occupant_to_existing_meeting(self, room_id, actor_name, occupant_name):
        room = self.get_meeting(room_id)
        if     not room \
            or not room.Active \
            or occupant_name in room.historical_occupant_names \
            or hasattr(self.meeting_container_storage.get(room.containerId), 'meeting_became_empty'):
            # exclude missing rooms, inactive rooms, rooms already left
            # by the occupant, and persistent rooms (that have their own
            # occupancy rules)
            logger.debug("%s not re-entering inactive/gone/previously-exited/persistent room %s/%s",
                         occupant_name, room, room_id)
            return None

        # TODO: We could centralize this type of checking with a convenience
        # utility somewhere.
        authorization_policy = component.queryUtility(IAuthorizationPolicy)
        if (    (   authorization_policy is None
                 or authorization_policy.permits(room, effective_principals(actor_name), ACT_ADD_OCCUPANT))
            and self.get_session_for(occupant_name) is not None):
            logger.debug("%s adding %s to room %s/%s",
                         actor_name, occupant_name, room, room_id)
            # broadcast the enter room event
            room.add_occupant_name(occupant_name)
            return room

        # otherwise, return none

    def get_meeting(self, room_id):
        return self.rooms.get(room_id)

    def exit_meeting(self, room_id, username):
        """
        :return: Value indicating successful exit.
        """
        result = None
        room = self.rooms.get(room_id)
        if room:
            result = room.del_occupant_name(username)
            if result:
                logger.debug("User, %s, exited room, %s, leaving %d occupants.",
                             username, room_id, len(room.occupant_names))
            if not room.occupant_names:
                # Note that since chat session handlers are not
                # tied to sessions, just names, and a name can have multiple
                # active sessions, and destroying a session
                # does not automatically cause that session to exit all rooms it was in
                # having rooms become in-Active is actually probably quite rare, especially for
                # something like a friends-list container
                # This has the following consequences:
                # - We don't drop our reference to it, so our rooms dictionary
                #   grows ever larger (fortunately, it's a btree)
                # - Meeting containers will probably keep re-entering the same meeting
                #   so its ID won't change
                # - Which in turn means that the transcript for the meeting will keep growing
                #   Ultimately this could cause problems.
                room.Active = False
                container = self.meeting_container_storage.get(room.containerId)
                if hasattr(container, 'meeting_became_empty'):
                    container.meeting_became_empty(self, room)

                # We do not (really) have the concept of persistent
                # meetings, merely persistent meeting containers.
                # Transcripts are probably in a different database and
                # so effectively have a weak reference to this meeting,
                # so GC must take that into account.
                if not room.Active:
                    del self.rooms[room_id]
        return result


deprecated('PersistentMappingMeetingStorage', 'No longer used')
class PersistentMappingMeetingStorage(PersistentMapping):
    pass
