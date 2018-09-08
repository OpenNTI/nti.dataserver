#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Chatserver functionality.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import six
import time

from zope import component
from zope import interface
from zope import deferredimport
from zope import lifecycleevent

from zope.event import notify

from BTrees.OOBTree import Set

from persistent import Persistent

from nti.common.sets import discard

from nti.chatserver._metaclass import _ChatObjectMeta

from nti.chatserver.interfaces import IMeeting
from nti.chatserver.interfaces import IChatserver
from nti.chatserver.interfaces import IMeetingPolicy
from nti.chatserver.interfaces import MeetingShouldChangeModerationStateEvent

from nti.externalization.datastructures import ExternalizableInstanceDict

from nti.externalization.interfaces import StandardExternalFields

from nti.externalization.representation import make_repr

from nti.property.property import alias
from nti.property.property import read_alias

from nti.threadable.externalization import ThreadableExternalizableMixin

from nti.threadable.threadable import Threadable as ThreadableMixin

from nti.zodb.minmax import MergingCounter

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

CLASS = StandardExternalFields.CLASS
MIMETYPE = StandardExternalFields.MIMETYPE

EVT_EXITED_ROOM = 'chat_exitedRoom'
EVT_ENTERED_ROOM = 'chat_enteredRoom'
EVT_POST_MESSOGE = 'chat_postMessage'
EVT_RECV_MESSAGE = 'chat_recvMessage'

logger = __import__('logging').getLogger(__name__)


@six.add_metaclass(_ChatObjectMeta)
@interface.implementer(IMeeting)
class _Meeting(ThreadableMixin,
               ThreadableExternalizableMixin,
               Persistent,
               ExternalizableInstanceDict):
    """
    Class to handle distributing messages to clients.
    """

    __emits__ = ('recvMessage', 'enteredRoom', 'exitedRoom',
                 'roomMembershipChanged', 'roomModerationChanged')

    _prefer_oid_ = False

    Active = True
    creator = None

    _v_chatserver = None

    _occupant_names = ()
    _moderation_state = None

    #: We use this to decide who can re-enter the room after exiting
    _historical_occupant_names = ()

    def __init__(self, chatserver=None):
        super(_Meeting, self).__init__()
        self._v_chatserver = chatserver
        self.id = None
        self.containerId = None
        self._MessageCount = MergingCounter(0)
        self.CreatedTime = time.time()
        self._occupant_names = Set()
        self._historical_occupant_names = Set()
        # Sometimes a room is created with a subset of the occupants that
        # should receive transcripts. The most notable case of this is
        # creating a room in reply to something that's shared: everyone
        # that it is shared with should get the transcript even if they
        # didn't participate in the room because they were offline.
        # Warning !!! How does this interact with things that are
        # shared publically and not specific users?
        self._addl_transcripts_to = Set()

    def _get_chatserver(self):
        return self._v_chatserver or component.queryUtility(IChatserver)

    def _set_chatserver(self, cs):
        self._v_chatserver = cs
    _chatserver = property(_get_chatserver, _set_chatserver)

    @property
    def MessageCount(self):
        # Can only set this directly, setting as a property
        # leads to false conflicts
        return self._MessageCount.value

    RoomId = alias('id')
    createdTime = alias('CreatedTime')  # ILastModified
    # ILastModified. Except we don't track it
    lastModified = read_alias('CreatedTime')

    ID = RoomId

    # IZContained
    __name__ = ID
    __parent__ = None

    def _Moderated(self):
        return self._moderation_state is not None

    def _setModerated(self, flag):
        if flag and self._moderation_state is None:
            notify(MeetingShouldChangeModerationStateEvent(self, flag))
            self.emit_roomModerationChanged(self._occupant_names, self)
        elif not flag and self._moderation_state is not None:
            notify(MeetingShouldChangeModerationStateEvent(self, flag))
            self.emit_roomModerationChanged(self._occupant_names, self)

    Moderated = property(_Moderated, _setModerated)

    @property
    def Moderators(self):
        return self._policy().moderated_by_usernames

    @property
    def occupant_session_names(self):
        """
        :return: An iterable of the names of all active users in this room.
                See :meth:`occupant_sessions`. Immutable
        """
        return set(self._occupant_names)  # copy, but still a set to comply with the interface
    occupant_names = occupant_session_names

    @property
    def historical_occupant_names(self):
        """
        :return: An immutable iterable of anyone who has even been active in this room.
        """
        return set(self._historical_occupant_names)
    sharedWith = historical_occupant_names # alias

    def _policy(self):
        return IMeetingPolicy(self)

    def post_message(self, msg_info):
        # pylint: disable=too-many-function-args
        result = self._policy().post_message(msg_info)
        if result == 1 and result is not True:
            self._MessageCount.increment()
        return result

    def add_additional_transcript_username(self, username):
        """
        Ensures that the user named `username` will get all appropriate transcripts.
        """
        self._addl_transcripts_to.add(username)

    def add_occupant_name(self, name, broadcast=True):
        """
        Adds the `session` to the group of sessions that are part of this room.
        :param bool broadcast: If `True` (the default) an event will
                be broadcast to the given session announcing it has entered the room.
                Set to False when doing bulk updates.
        """
        sess_count_before = len(self._occupant_names)
        self._occupant_names.add(name)
        self._historical_occupant_names.add(name)
        sess_count_after = len(self._occupant_names)
        if broadcast and sess_count_after != sess_count_before:
            # Yay, we added one!
            self.emit_enteredRoom(name, self)
            self.emit_roomMembershipChanged(self.occupant_names - set((name,)),
                                            self)
            # notify
            lifecycleevent.modified(self)
        else:
            logger.debug("Not broadcasting (%s) enter/change events for %s in %s",
                         broadcast, name, self)

    def add_occupant_names(self, names, broadcast=True):
        """
        Adds all sessions contained in the iterable `names` to this group
        and broadcasts an event to each new member.
        :param bool broadcast: If ``True`` (the default) an event will
                be broadcast to all new members and to all old members.
        """
        new_members = set(names).difference(self.occupant_names)
        old_members = self.occupant_names - new_members
        self._occupant_names.update(new_members)
        self._historical_occupant_names.update(names)
        if broadcast:
            self.emit_enteredRoom(new_members, self)
            self.emit_roomMembershipChanged(old_members, self)
        if new_members:
            lifecycleevent.modified(self)

    def del_occupant_name(self, name):
        if name in self._occupant_names:
            discard(self._occupant_names, name)
            self.emit_exitedRoom(name, self)
            self.emit_roomMembershipChanged(self._occupant_names, self)
            return True

    def add_moderator(self, mod_name):
        # pylint: disable=too-many-function-args
        self._policy().add_moderator(mod_name)

    def is_moderated_by(self, mod_name):
        return self._moderated.is_moderated_by(mod_name)

    def approve_message(self, msg_id):
        # pylint: disable=too-many-function-args
        return self._policy().approve_message(msg_id)

    def shadow_user(self, username):
        # pylint: disable=too-many-function-args
        return self._policy().shadow_user(username)

    def toExternalDictionary(self, mergeFrom=None, *args, **kwargs):  # pylint: disable=keyword-arg-before-vararg
        result = dict(mergeFrom) if mergeFrom else dict()
        result[CLASS] = 'RoomInfo'
        result[MIMETYPE] = 'application/vnd.nextthought.roominfo'
        result['Moderated'] = self.Moderated
        # sets can't go through JSON
        result['MessageCount'] = self.MessageCount
        result['Moderators'] = list(self.Moderators)
        result['Occupants'] = list(self.occupant_names)
        # Warning !!!: Handling shadowing and so on.
        return super(_Meeting, self).toExternalDictionary(mergeFrom=result, *args, **kwargs)

    def updateFromExternalObject(self, parsed, *args, **kwargs):  # pylint: disable=arguments-differ
        addl_ts_needs_reset = self.inReplyTo
        super(_Meeting, self).updateFromExternalObject(parsed, *args, **kwargs)
        try:
            if addl_ts_needs_reset is not None and self.inReplyTo != addl_ts_needs_reset:
                self._addl_transcripts_to.clear()
            new_targets = self.inReplyTo.flattenedSharingTargetNames
            self._addl_transcripts_to.update(new_targets)
        except AttributeError:
            pass

    # pylint: disable=protected-access
    __repr__ = make_repr(lambda self: "<%s %s %s>" % (self.__class__.__name__,
                                                      self.ID,
                                                      self._occupant_names))

deferredimport.initialize()
deferredimport.deprecatedFrom(
    "Moved to nti.chatserver._meeting_post_policy",
    "nti.chatserver._meeting_post_policy",
    "_ModeratedMeetingState")

deferredimport.deprecated(
    "Import from _Meeting instead",
    _ChatRoom='nti.chatserver.meeting:_Meeting',
   _ModeratedMeeting='nti.chatserver.meeting:_Meeting',
   _ModeratedChatRoom='nti.chatserver.meeting:_Meeting')
