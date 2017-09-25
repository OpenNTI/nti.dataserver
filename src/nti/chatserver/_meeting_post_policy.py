#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import six
import functools
import collections

from zope import component
from zope import interface

from zope.event import notify

from zope.intid.interfaces import IIntIds

import BTrees

from persistent import Persistent

from nti.chatserver import MessageFactory as _

from nti.chatserver._metaclass import _ChatObjectMeta

from nti.chatserver.interfaces import STATUS_POSTED
from nti.chatserver.interfaces import STATUS_PENDING
from nti.chatserver.interfaces import STATUS_SHADOWED

from nti.chatserver.interfaces import CHANNELS
from nti.chatserver.interfaces import CHANNEL_STATE
from nti.chatserver.interfaces import CHANNEL_DEFAULT
from nti.chatserver.interfaces import CHANNEL_WHISPER

from nti.chatserver.interfaces import IMeeting
from nti.chatserver.interfaces import IMeetingPolicy
from nti.chatserver.interfaces import IMessageInfoStorage
from nti.chatserver.interfaces import MessageInfoPostedToRoomEvent
from nti.chatserver.interfaces import IMeetingShouldChangeModerationStateEvent

from nti.ntiids.ntiids import is_valid_ntiid_string

from nti.socketio.interfaces import SocketEventHandlerClientError

logger = __import__('logging').getLogger(__name__)


class MessageTooBig(SocketEventHandlerClientError):
    """
    Raised when a policy is asked to post a message that exceeds the size limits.
    """


@six.add_metaclass(_ChatObjectMeta)
@interface.implementer(IMeetingPolicy)
class _MeetingMessagePostPolicy(object):
    """
    Class that actually emits the messages
    """

    __emits__ = ('recvMessage', 'enteredRoom', 'exitedRoom',
                 'roomMembershipChanged', 'roomModerationChanged')

    def __init__(self, chatserver=None, room=None, occupant_names=(), transcripts_to=()):
        self._room = room  # We need the room so we can emit the right notify() events
        self._room_id = room.ID if room is not None else None
        self._chatserver = chatserver
        self._occupant_names = occupant_names
        self._addl_transcripts_to = transcripts_to

    def _ensure_message_stored(self, msg_info):
        """
        For messages that can take an OID, call this to ensure that
        they have one. Must be called during a transaction.

        .. note:: FIXME: This is badly broken. Messages currently have
                no actual home; nothing owns them or is their location. They
                badly need one, a real container. Then all of this goes away.

        :return: Undefined.
        """
        storage = IMessageInfoStorage(msg_info)
        storage.add_message(msg_info)

    def _treat_recipients_like_default_channel(self, msg_info):
        return (   msg_info.is_default_channel()  # Actually on the default channel
                or not msg_info.recipients_without_sender  # No recipient list
                or msg_info.channel == CHANNEL_STATE)  # state update

    def _get_recipient_names_for_message(self, msg_info):
        if self._treat_recipients_like_default_channel(msg_info):
            recipient_names = set(self._occupant_names)
        else:
            requested = set(msg_info.recipients_with_sender)
            recipient_names = set(self._occupant_names).intersection(requested)
        recipient_names.discard(None)
        return recipient_names

    def _names_excluded_when_considering_all(self):
        """
        :return: A set of sids excluded when comparing against all occupants.
        """
        return set()

    def _is_message_to_all_occupants(self, msg_info, recipient_names=None):
        """
        Should the message be treated as if it were the default
        channel? Yes, if it is either to the DEFAULT channel, an empty recipient list, or its recipient list
        is to everyone (not excluded by :meth:`_names_excluded_when_considering_all`)
        """
        if self._treat_recipients_like_default_channel(msg_info):
            return True
        recipients = recipient_names or self._get_recipient_names_for_message(msg_info)
        occupants = set(self._occupant_names) - self._names_excluded_when_considering_all()
        return recipients == occupants

    def _post_message_should_handle_message_channel(self, msg_info):
        """
        Called by :meth:`post_message` to determine whether it should be passed through
        the usual handling rules. This class's implementation of `post_message` applies
        no security rules and only understands the simplest content types, so we only
        pass through the basic message types, plus the builtin-in chat status types.
        """
        return (msg_info.channel or CHANNEL_DEFAULT) in (CHANNEL_DEFAULT, CHANNEL_WHISPER, CHANNEL_STATE)

    def _post_message_should_handle_channel_as_default(self, unused_msg_info):
        """
        Called if there is no specific handler for the channel. If True, then the default handler
        will be used. This implementation does not handle any other channels.
        """
        return False

    #: Research indicates that AIM uses a 1024 byte limit for the body (including formatting!)
    #: while MSN uses a much smaller limit of 400 characters (though that's enforced on the client
    #: and can be raised with hacks to a few thousand)
    MAX_BODY_SIZE = 1024

    def _does_message_conform_to_limits(self, msg_info):
        """
        Answers whether the message conforms to the general limits established, such
        as body size, etc.
        """

        # Recall that different channels can have different types
        # of bodies, currently either an array of strings/canvas objects or a mapping.
        # The channels that this class supports only accept the list-of-strings/canvas objects;
        # this method is bypassed for the moderation channels

        # so this counts all formatted text, plus number of objects in canvases
        # (do we want that?)
        body_len = sum((len(x) for x in msg_info.body or ()))
        return body_len <= self.MAX_BODY_SIZE

    def post_message(self, msg_info):
        """
        Post the :class:`.IMessageInfo` to the room.

        :return: A value that can be interpreted as a boolean, indicating success of posting
                the message. If the value is a number and not a bool object, then it is the
                number by which the general message count of the room should be incremented (currently only one).
        """
        # TODO: Got to modify the handler interaction to be able to inform
        # the client about these problems
        if not self._post_message_should_handle_message_channel(msg_info):
            logger.debug("Dropping message on unsupported channel %s",
                         msg_info)
            return False

        # Then we better have a handler function for it
        handler = getattr(self,
                          '_post_message_handle_' +
                          str(msg_info.channel or CHANNEL_DEFAULT),
                          self._post_message_handle_DEFAULT if self._post_message_should_handle_channel_as_default(msg_info) else None)

        return handler(msg_info)

    def _post_message_handle_DEFAULT(self, msg_info):

        if not self._does_message_conform_to_limits(msg_info):
            logger.debug("Dropping message due to size limit")
            # partial support for handling too big messages and getting it back
            # to the client
            raise MessageTooBig(_("The message is too big. It can contain a maximum of ${parts} characters or shapes",
                                  mapping={'parts': self.MAX_BODY_SIZE}))

        result = True
        # TODO: How to handle messages from senders that do not occupy this room?
        # In the ordinary case, would we want to drop them?
        # It becomes complicated in the moderated case where there may
        # be a delay involved.
        msg_info.Status = STATUS_POSTED
        # Ensure it's this room, thank you.
        msg_info.containerId = self._room_id
        # Ensure there's an OID
        if msg_info.__parent__ is None:
            self._ensure_message_stored(msg_info)

        transcript_owners = set(self._addl_transcripts_to)
        transcript_owners.add(msg_info.Sender)

        # Accumulate the session IDs of everyone who should get a copy.
        # Note that may or may not include the sender--hence transcript_owners.
        # (See note above)
        recipient_names = self._get_recipient_names_for_message(msg_info)

        if self._is_message_to_all_occupants(msg_info, recipient_names=recipient_names):
            # recipients are ignored for the default channel,
            # and a message to everyone also counts for incrementing the ids.
            result = 1
            self.emit_recvMessage(recipient_names, msg_info)
        else:
            # On a non-default channel, and not to everyone in the room
            for name in recipient_names:
                self.emit_recvMessage(name, msg_info)

        # Emit events
        # ObjectAdded ensures registered for intid, but we're actually doing that in _ensure_stored
        # lifecycleevent.added( msg_info, msg_info.__parent__, msg_info.__name__ )
        notify(MessageInfoPostedToRoomEvent(msg_info,
                                            transcript_owners | recipient_names,
                                            self._room))

        # Everyone who gets the transcript also
        # is considered to be on the sharing list
        sharedWith = set(recipient_names)
        sharedWith.update(transcript_owners)
        msg_info.setSharedWithUsernames(sharedWith)
        # In principal, we might be able to share some data and reduce
        # pickling using a persistent set. In practice, at least for small
        # sharing lists, it doesn't make any difference.
        # msg_info.sharedWith = BTrees.OOBTree.OOSet( msg_info.sharedWith )
        return result

    #: Whispers are handled the same as default
    _post_message_handle_WHISPER = _post_message_handle_DEFAULT

    def _post_message_handle_STATE(self, msg_info):
        STATES = ('active', 'composing', 'paused', 'inactive', 'gone')
        if      not isinstance(msg_info.body, collections.Mapping) \
            or 'state' not in msg_info.body or msg_info.body['state'] not in STATES:
            return False

        # Ok, great. Send it to everyone without storing it or transcripting it
        # or incrementing room message counts
        msg_info.body = {'state': msg_info.body['state']}  # drop unknown keys
        recipient_names = self._get_recipient_names_for_message(msg_info)
        self.emit_recvMessage(recipient_names, msg_info)
        return True

    # ##
    # Things this policy doesn't implement
    # ##

    @property
    def moderated_by_usernames(self):
        return ()

    def add_moderator(self, mod_name):
        raise NotImplementedError()  # pragma: no cover

    def shadow_user(self, username):
        raise NotImplementedError()  # pragma: no cover

    def approve_message(self, msg_id):
        raise NotImplementedError()  # pragma: no cover


class _ModeratedMeetingState(Persistent):

    family = BTrees.family64

    def __init__(self, family=None):
        self._moderated_by_names = BTrees.OOBTree.Set()
        self._shadowed_usernames = BTrees.OOBTree.Set()
        # A BTree isn't necessarily the most efficient way
        # to implement the moderation queue, but it does work.
        # We will typically have many writers and one reader--
        # but that reader, the moderator, is also writing.
        if family is not None:
            self.family = family
        else:
            intids = component.queryUtility(IIntIds)
            if intids is not None:
                self.family = intids.family

        self._moderation_queue = self.family.OI.BTree()

    @property
    def moderated_by_usernames(self):
        return frozenset(self._moderated_by_names)

    Moderators = moderated_by_usernames

    def shadowUser(self, username):
        """
        Causes all messages on non-default channels
        from or to this sender to be posted to all
        the moderators as well.
        """
        self._shadowed_usernames.add(username)
        return True

    @property
    def shadowed_usernames(self):
        return frozenset(self._shadowed_usernames)

    def add_moderator(self, mod_name):
        self._moderated_by_names.add(mod_name)

    def is_moderated_by(self, mod_name):
        return mod_name in self._moderated_by_names

    def hold_message_for_moderation(self, msg_info):
        # TODO: Are we 100% sure that this is safe? IDs will never
        # overlap (I think we are, they are UUIDs, we should probably add
        # a check
        assert msg_info.MessageId and msg_info.MessageId not in self._moderation_queue
        intids = component.queryUtility(IIntIds)
        self._moderation_queue[msg_info.MessageId] = intids.getId(msg_info)
        msg_info.Status = STATUS_PENDING

    def approve_message(self, msg_id):
        # TODO: Disapprove messages? This queue could get terrifically
        # large.
        msg = None
        msg_iid = self._moderation_queue.pop(msg_id, None)
        if msg_iid:
            msg = component.getUtility(IIntIds).queryObject(msg_iid)

        if msg:
            msg.Status = STATUS_POSTED
        else:
            logger.warn("Attempted to approve message ID that does not exist in queue: %s",
                        msg_id)
        return msg


def _bypass_for_moderator(f):
    """
    The decorated function simply calls through to the superclass if the message sender is a moderator
    """
    @functools.wraps(f)
    def bypassing(self, msg_info):
        if self.is_moderated_by(msg_info.Sender):
            super(_ModeratedMeetingMessagePostPolicy, self).post_message(msg_info)
            return True
        return f(self, msg_info)
    return bypassing


def _only_for_moderator(f):
    """
    The decorated function can only be called if the message sender is a moderator; otherwise return false
    """
    @functools.wraps(f)
    def enforcing(self, msg_info):
        if not self.is_moderated_by(msg_info.Sender):
            return False
        return f(self, msg_info)
    return enforcing


def _always_true_for_moderator(f):
    """
    The decorated function is always true if the message sender is a moderator; otherwise the function is run
    """
    @functools.wraps(f)
    def bypassing(self, msg_info):
        if self.is_moderated_by(msg_info.Sender):
            return True
        return f(self, msg_info)
    return bypassing


@six.add_metaclass(_ChatObjectMeta)
class _ModeratedMeetingMessagePostPolicy(_MeetingMessagePostPolicy):
    """
    A chat room that moderates messages.
    """

    __emits__ = ('recvMessageForModeration', 'recvMessageForShadow')

    def __init__(self, *args, **kwargs):
        self.moderation_state = kwargs.pop('moderation_state')
        super(_ModeratedMeetingMessagePostPolicy, self).__init__(*args, **kwargs)

    @property
    def moderated_by_usernames(self):
        return self.moderation_state.moderated_by_usernames

    Moderators = moderated_by_usernames

    def shadow_user(self, username):
        return self.moderation_state.shadowUser(username)

    @property
    def shadowed_usernames(self):
        return self.moderation_state.shadowed_usernames

    def _names_excluded_when_considering_all(self):
        """
        For purposes of calculating if a message is to everyone,
        we ignore the moderators. This prevents whispering to the entire
        room, minus the teachers.
        """
        return self.moderated_by_usernames

    def _post_message_should_handle_message_channel(self, msg_info):
        """
        If we pass something through to the default :meth:`post_message`, then it should be handled.
        """
        return (msg_info.channel or CHANNEL_DEFAULT) in CHANNELS

    def _post_message_should_handle_channel_as_default(self, unused_msg_info):
        """
        If we post something through to the default :meth:`post_message`, then handle it as default.
        """
        return True

    @_always_true_for_moderator
    def _does_message_conform_to_limits(self, msg_info):
        return super(_ModeratedMeetingMessagePostPolicy, self)._does_message_conform_to_limits(msg_info)

    def post_message(self, msg_info):
        # In moderated rooms, we break each channel out
        # to a separate function for ease of permissioning.
        msg_info.containerId = self._room_id
        channel = msg_info.channel or CHANNEL_DEFAULT
        handler = getattr(self, '_msg_handle_' + str(channel), None)
        handled = False
        if handler:
            # We have a handler, but it still may not pass the pre-conditions,
            # so we don't store it here.
            handled = handler(msg_info)

        if not handled:
            if handler:
                logger.debug('Handler (%s) rejected message (%s) sent by %s/%s (moderators: %s)',
                             handler, msg_info, msg_info.Sender, msg_info.Sender, self.moderated_by_usernames)
            else:
                logger.debug(
                    'Dropping message on unknown channel %s', msg_info)
        return handled

    def _can_sender_whisper_to(self, msg_info):
        """
        Can the sender whisper to the recipients?
        Use case: The TA can whisper to anyone, students
        can only whisper to the TA. We do allow
        one-on-one whispering.
        """
        # Right now we just use one "role" for this concept,
        # that of moderator. This will probably change.
        return msg_info.Sender in self.moderated_by_usernames \
            or all(recip in self.moderated_by_usernames for recip in msg_info.recipients_without_sender) \
            or len(msg_info.recipients_without_sender) == 1

    def _do_shadow_message(self, msg_info):
        if any(recip in self.shadowed_usernames
               for recip in msg_info.recipients_with_sender):
            msg_info.Status = STATUS_SHADOWED
            self._ensure_message_stored(msg_info)
            self.emit_recvMessageForShadow(self.moderated_by_usernames, msg_info)
            notify(MessageInfoPostedToRoomEvent(msg_info,
                                                self.moderated_by_usernames,
                                                self._room))

    def _msg_handle_STATE(self, unused_msg_info):
        """
        Moderated chats (multi-user chats by definition) simply do not transmit state info.

        We may change this to be transmitted just for the moderators.
        """
        return True  # handled so don't log, just don't do anything

    @_bypass_for_moderator
    def _msg_handle_WHISPER(self, msg_info):
        if     self._is_message_to_all_occupants(msg_info) \
           and len(msg_info.recipients_without_sender) > 1:
            # Whispering to everyone is just like posting to the default
            # channel. We make a special exception when there's only
            # one other person besides the moderator in the room,
            # to enable peer-to-peer whispering
            return self._msg_handle_DEFAULT(msg_info)

        if self._can_sender_whisper_to(msg_info):
            self._do_shadow_message(msg_info)
            super(_ModeratedMeetingMessagePostPolicy, self).post_message(msg_info)
            return True

    @_bypass_for_moderator
    def _msg_handle_DEFAULT(self, msg_info):
        if not self._does_message_conform_to_limits(msg_info):
            return False
        self._ensure_message_stored(msg_info)
        self.moderation_state.hold_message_for_moderation(msg_info)
        self.emit_recvMessageForModeration(self.moderated_by_usernames, msg_info)
        return True

    @_only_for_moderator
    def _msg_handle_CONTENT(self, msg_info):
        if    not isinstance(msg_info.body, collections.Mapping) \
           or not 'ntiid' in msg_info.body \
           or not is_valid_ntiid_string(msg_info.body['ntiid']):
            return False
        # sanitize any keys we don't know about.
        msg_info.body = {'ntiid': msg_info.body['ntiid']}
        # Recipients are ignored, message goes to everyone
        msg_info.recipients = []
        # And now broadcast
        super(_ModeratedMeetingMessagePostPolicy, self).post_message(msg_info)
        return True

    @_only_for_moderator
    def _msg_handle_META(self, msg_info):
        # Right now, we support two actions. As this grows,
        # we'll need to refactor appropriately, like with channels.
        ACTIONS = ('pin', 'clearPinned')
        if    not isinstance(msg_info.body, collections.Mapping) \
           or 'channel' not in msg_info.body or msg_info.body['channel'] not in CHANNELS \
           or 'action' not in msg_info.body or msg_info.body['action'] not in ACTIONS:
            return False

        # In all cases, these are broadcasts
        msg_info.recipients = ()
        if msg_info.body['action'] == 'pin':
            if not is_valid_ntiid_string(msg_info.body.get('ntiid', None)):
                return False
            # sanitize the body
            msg_info.body = {k: msg_info.body[k]
                             for k in ('channel', 'action', 'ntiid')}
            super(_ModeratedMeetingMessagePostPolicy, self).post_message(msg_info)
        elif msg_info.body['action'] == 'clearPinned':
            # sanitize the body
            msg_info.body = {
                k: msg_info.body[k] for k in ('channel', 'action')
            }
            super(_ModeratedMeetingMessagePostPolicy, self).post_message(msg_info)
        else:  # pragma: no cover
            # Impossible to get here due to the check above; left in place
            # to help us add more actions safely
            raise AssertionError('Meta action ' + str(msg_info.body['action']))

        return True

    def _msg_handle_POLL(self, msg_info):
        if self.is_moderated_by(msg_info.Sender):
            # TODO: Track the OIDs of these messages so we can
            # validate replies
            # TODO: Validate body, when we decide what that is
            # This is a broadcast (TODO: Always?)
            msg_info.recipients = ()
            super(_ModeratedMeetingMessagePostPolicy, self).post_message(msg_info)
            return True

        if not msg_info.inReplyTo:
            # TODO: Track replies.
            return False

        # replies (answers) go only to the moderators
        msg_info.recipients = self.moderated_by_usernames
        return super(_ModeratedMeetingMessagePostPolicy, self).post_message(msg_info)

    def add_moderator(self, mod_name):
        self.moderation_state.add_moderator(mod_name)
        self.emit_roomModerationChanged(self._occupant_names, self._room)

    def is_moderated_by(self, mod_name):
        return self.moderation_state.is_moderated_by(mod_name)

    def approve_message(self, msg_id):
        msg = self.moderation_state.approve_message(msg_id)
        if msg:
            return super(_ModeratedMeetingMessagePostPolicy, self).post_message(msg)


@component.adapter(IMeeting, IMeetingShouldChangeModerationStateEvent)
def meeting_should_change_moderation_state(self, unused_event):
    if self._moderation_state is None:
        self._moderation_state = _ModeratedMeetingState()
    else:
        self._moderation_state = None


@component.adapter(IMeeting)
@interface.implementer(IMeetingPolicy)
def MeetingPostPolicy(self):
    """
    Adapter from a meeting to its policy.

    .. note:: This is currently intricately tied to the meeting.
    """
    if self._moderation_state:
        policy = _ModeratedMeetingMessagePostPolicy(self._chatserver,
                                                    room=self,
                                                    occupant_names=self._occupant_names,
                                                    transcripts_to=self._addl_transcripts_to,
                                                    moderation_state=self._moderation_state)
    else:
        policy = _MeetingMessagePostPolicy(self._chatserver,
                                           room=self,
                                           occupant_names=self._occupant_names,
                                           transcripts_to=self._addl_transcripts_to)
    return policy
