#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Interfaces having to do with chat.

.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=inherit-non-class,inconsistent-mro

import six

from zope import component
from zope import interface

from zope.interface.interfaces import IObjectEvent

from zope.interface.interfaces import ObjectEvent

from zope.security.permission import Permission

from nti.contentfragments.schema import PlainTextLine

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IZContained
from nti.dataserver.interfaces import ILastModified
from nti.dataserver.interfaces import IModeledContent
from nti.dataserver.interfaces import IUserGeneratedData
from nti.dataserver.interfaces import IModeledContentBody
from nti.dataserver.interfaces import IShareableModeledContent

from nti.dataserver.interfaces import UserNotificationEvent
from nti.dataserver.interfaces import CompoundModeledContentBody

from nti.socketio.interfaces import ISocketEventHandler

from nti.schema.field import Set
from nti.schema.field import Bool
from nti.schema.field import Dict
from nti.schema.field import Float
from nti.schema.field import Object
from nti.schema.field import Variant
from nti.schema.field import UniqueIterable
from nti.schema.field import ValidChoice as Choice
from nti.schema.field import DecodingValidTextLine as TextLine

ACT_ENTER = Permission('nti.chatserver.actions.enter')
ACT_MODERATE = Permission('nti.chatserver.actions.moderate')
ACT_ADD_OCCUPANT = Permission('nti.chatserver.actions.add_occupant')

CHANNEL_POLL = u'POLL'
CHANNEL_META = u'META'
CHANNEL_STATE = u'STATE'
CHANNEL_DEFAULT = u'DEFAULT'
CHANNEL_WHISPER = u'WHISPER'
CHANNEL_CONTENT = u'CONTENT'
CHANNELS = (CHANNEL_DEFAULT, CHANNEL_WHISPER, CHANNEL_CONTENT,
            CHANNEL_POLL, CHANNEL_META, CHANNEL_STATE)

STATUS_POSTED = u'st_POSTED'
STATUS_INITIAL = u'st_INITIAL'
STATUS_PENDING = u'st_PENDING'
STATUS_SHADOWED = u'st_SHADOWED'
STATUSES = (STATUS_INITIAL, STATUS_PENDING, STATUS_POSTED, STATUS_SHADOWED)


class IChatserver(interface.Interface):
    pass


class IChatEventHandler(ISocketEventHandler):
    """
    Marker interface for objects designed specifically as chat
    event handlers. These will typically be registered as a multi-adapter
    on the combination ``(user, session, chatserver)``.
    """


class IMeeting(IModeledContent, IZContained):
    """
    Provides the storage structure for a meeting.

    Policy decisions about whether and how to post messages, add/remove occupants
    are delegated to a :class:`IMeetingPolicy` object, which is not expected
    to be persistent and which is created on demand.
    """

    creator = TextLine(title=u"Meeting creator",
                       description=u"User that started the meeting")

    RoomId = TextLine(title=u"Meeting identifier",
                      description=u"Meeting identifier")

    CreatedTime = Float(title=u"Meeting creation time",
                        description=u"Meeting creation time")

    Moderated = Bool(title=u"Whether the meeting is being moderated or not.",
                     description=u"Toggling this changes the policy in use.")

    Active = Bool(title=u"Whether the meeting is currently active")

    occupant_names = Set(
        title=u"A set of the string names of members currently in the meeting; immutable."
    )

    historical_occupant_names = Set(
        title=u"A set of the string names of anyone who has ever been a member of this meeting; immutable."
    )


class IMeetingShouldChangeModerationStateEvent(IObjectEvent):
    """
    Emitted when the :class:`IMeeting` will be changing moderation state.
    """

    moderated = Bool(title=u"Whether the meeting should become moderated")


@interface.implementer(IMeetingShouldChangeModerationStateEvent)
class MeetingShouldChangeModerationStateEvent(ObjectEvent):

    def __init__(self, o, flag):
        super(MeetingShouldChangeModerationStateEvent, self).__init__(o)
        self.moderated = flag


class IMeetingPolicy(interface.Interface):
    """
    The policy for posting messages to a room. Typically this will
    be an adapter from an :class:`IMeeting`. Responsible for sending events
    to connected sockets.
    """

    def post_message(msg_info):
        """
        :param msg_info: An :class:`IMessageInfo` object.
        :return: A value that can be interpreted as a boolean, indicating success of posting
                the message. If the value is a number and not a `bool` object, then it is the
                number by which the general message count of the room should be incremented (currently only one).
        """

    def add_moderator(mod_name):
        """
        Add a moderator to the room.
        If a moderator was added, emits an event across the sockets of all connected
        users.
        """

    def approve_message(msg_id):
        """
        Optional; raises an error if not supported.
        """

    def shadow_user(username):
        """
        Cause future messages to the user specified by `username` to be copied
        to the moderators of this room.
        :return: Boolean value indicating whether the username was shadowed.
        """

    moderated_by_usernames = interface.Attribute(
        "Iterable of names moderating this meeting."
    )


class IMessageInfo(IShareableModeledContent,
                   IUserGeneratedData,
                   IZContained,
                   IModeledContentBody):
    # We have to be IShareableModeledContent if we want the same ACL provider to work for us
    # as works for Notes
    channel = Choice(title=u"The channel the message was sent to.",
                     values=CHANNELS)

    Status = Choice(title=u"The status of the message. Set by the server.",
                    values=STATUSES)

    Creator = TextLine(title=u"Message creator",
                       description=u"User that send this message")

    body = Variant((Dict(key_type=TextLine()),  # , value_type=schema.TextLine() ),
                    CompoundModeledContentBody()),
                   description=u"The body is either a dictionary of string keys and values, or a Note body")

    recipients = UniqueIterable(
        title=u"The names of all the recipients of the message.",
        description=u"""The actual recipients of the message, whether or not they are "
                    u"named in the message itself. Includes people who just get the transcript.""",
        value_type=TextLine())


class IMessageInfoEvent(IObjectEvent):
    """
    An event having to do with an :class:`IMessageInfo`.
    """


@interface.implementer(IMessageInfoEvent)
class MessageInfoEvent(ObjectEvent):
    pass


class IMessageInfoPostedToRoomEvent(IMessageInfoEvent):
    """
    A message has been delivered to a room.
    """

    recipients = Set(title=u"The names of all the recipients of the message.",
                     description=u"""The actual recipients of the message, whether or not they are
                     named in the message itself. Includes people who just get the transcript.""",
                     value_type=TextLine())

    room = Object(IMeeting,
                  title=u"The room that the message was posted to")


@interface.implementer(IMessageInfoPostedToRoomEvent)
class MessageInfoPostedToRoomEvent(MessageInfoEvent):

    def __init__(self, obj, recipients, room):
        super(MessageInfoPostedToRoomEvent, self).__init__(obj)
        self.recipients = recipients
        self.room = room


class IMeetingContainer(interface.Interface):

    def create_meeting_from_dict(chatserver, meeting_dict, constructor):
        """
        Called to create (or return) a meeting instance within this container.
        Typically, security will be based on the creator being allowed
        to create a meeting.
        :param chatserver: The chatserver.
        :param Mapping meeting_dict: The description of the room. You may modify
                this. If it has an 'Occupants' key, it will be an iterable of usernames or
                (username, sid) tuples.
        """

    def meeting_became_empty(chatserver, meeting):
        """
        Called to notify that all occupants have left the meeting. The
        meeting will be declared inactive and deleted from
        the chatserver. It may be reactivated by this method, in which case
        it will not be deleted from the chatserver.
        """

    def enter_active_meeting(chatserver, meeting_dict):
        """
        Called when someone wants to enter an active room (if there is one).
        Typically, security will be based on the creator being allowed to occupy the
        meeting.
        :param meeting_dict: Guaranteed to have at least the Creator.
                May be modified. If this method fails (returns None), our caller may call :meth:create_meeting_from_dict
                with this same dictionary.
        :return: The active room, if successfully entered, otherwise None.
        """

    def create_or_enter_meeting(chatserver, meeting_dict, constructor):
        """
        The combination of :meth:`create_or_enter_meeting` with :meth:`enter_active_meeting`.
        If an active meeting exists and the ``Creator`` is allowed to occupy it,
        then it will be returned. Otherwise, if the ``Creator`` is allowed to create
        one then it will be returned.
        :return: A tuple (meeting or None, created). If the first param is not None, the second
                param will say whether it was already active (False) or freshly created (True).
        """


class IMeetingStorage(interface.Interface):
    """
    An object for the storage of meetings. The general
    contract is that meetings will be added to this object when
    they are created, and when they become unactive, they will
    be deleted. (However, a storage instance is allowed to let
    the room's lifetime extend beyond that).
    """

    def get(room_id):  # pylint: disable=arguments-differ
        """
        Returns the stored room having the given ID, or None
        if there is no room with that Id stored in this object.
        This should be sure to only return :class:`IMeeting` objects.
        """

    def __getitem__(room_id):
        """
        Returns the stored room with that ID or raises KeyError.
        """

    def add_room(room):
        """
        Stores a room in this object. Sets the room's (an IContained)
        ``id`` property to be in the form produced by
        :func:`nti.ntiids.oids.to_external_ntiid_oid` (or,
        at a minimum, to be a valid NTIID, probably of type :const:`nti.ntiids.ntiids.TYPE_UUID`).

        Ensures that the room is persistently stored before returning.
        May also register the room with ``intid`` utilities.
        """
        # Consumers of Meetings (e.g., chat_transcripts) depend on the ID being
        # a valid NTIID. They like to be able to find the object later based just on
        # this NTIID. They also like to be able to deriver new IDs from this
        # NTIID (all of that is weird)

    def __delitem__(room_id):
        """
        Removes the room stored in this object with the given id or
        raises KeyError. May be ignored.
        """


class IMessageInfoStorage(interface.Interface):
    """
    Something that can persistently store chat messages that are
    being sent.
    Ideally, there will be an adapter registered to connect messages
    to users and hang the messages off of the user.
    """

    def add_message(msg_info):
        """
        Cause the message to be stored. Typically, this will
        be done using a :class:`zope.container.interfaces.IContainer`
        and so events will be emitted and ``intids``  will be assigned.
        """

    def remove_message(msg_info):
        """
        Remove the specifed message info
        """


class IUserTranscriptStorage(interface.Interface):
    """
    An object that knows how to store transcripts for users
    in a meeting.
    """

    meetings = interface.Attribute("Return all Meetings objects")

    transcripts = interface.Attribute("Return all Transcript objects")

    transcript_summaries = interface.Attribute(
        "Return all Transcript summary objects"
    )

    def transcript_for_meeting(meeting_id):
        pass

    def add_message(meeting, msg):
        pass

    def remove_message(meeting, msg):
        pass


# Presence


class IUnattachedPresenceInfo(interface.Interface):
    """
    Basic description of what goes into generic presence info.
    """

    type = Choice(title=u"What kind of presence this describes",
                  values=(u'available', u'unavailable'),
                  default=u'available',
                  required=True)

    show = Choice(title=u"A hint of how the UI should present the user",
                  values=(u'away', u'chat', u'dnd', u'xa'),
                  default=u'chat',
                  required=False)

    status = PlainTextLine(title=u"Optional plain text status information",
                           required=False,
                           max_length=140)


class IPresenceInfo(IUnattachedPresenceInfo, ILastModified):
    """
    A description of the chat presence for a particular user.
    """
    username = TextLine(title=u"The global username to which this presence applies.",
                        description=u"If set when reading from external, may be ignored and replaced with canonical value.",
                        required=False)

    def isAvailable():
        """
        Does the presence represent a user who is available for chat/chat APIs?
        """


class IContacts(interface.Interface):
    """
    Something that can report on the "friends" or "buddy list" or "contact list"
    of a particular entity. This may or may not be persistent and editable
    by the entity (it may be derived from other information). This is intended
    to be used by adapting the entity to this interface.
    """

    __parent__ = Object(IUser, title=u"The owner of this contact list")

    contactNamesSubscribedToMyPresenceUpdates = UniqueIterable(title=u"The usernames of buddies that should get updates when the owner's presence changes",
                                                               description=u"Probably computed as a property",
                                                               value_type=TextLine(title=u"A username"))

    contactNamesISubscribeToPresenceUpdates = UniqueIterable(title=u"The usernames of buddies that the owner wants presence updates for",
                                                             description=u"Probably computed as a property",
                                                             value_type=TextLine(title=u"A username"))


class IContactsModifiedEvent(IObjectEvent):
    """
    Fired when the contacts for a user are modified.
    Specific subinterfaces should be listened to.
    """

    object = Object(IUser, title=u"The user who's contacts changed.")
    contacts = Object(IContacts, title=u"The contacts of the user")


class IContactISubscribeToAddedToContactsEvent(IContactsModifiedEvent):
    """
    Fired when a contact whose presence I (the object of this event) want updates
    about is added to my contacts.
    """

    contact = Object(IUser, title=u"The user that I now want updates about.")


@interface.implementer(IContactsModifiedEvent)
class ContactsModifiedEvent(ObjectEvent):

    def __init__(self, user):  # pylint: disable=useless-super-delegation
        super(ContactsModifiedEvent, self).__init__(user)

    @property
    def contacts(self):
        return IContacts(self.object)


@interface.implementer(IContactISubscribeToAddedToContactsEvent)
class ContactISubscribeToAddedToContactsEvent(ContactsModifiedEvent):

    def __init__(self, contact_owner, contact_added):
        super(ContactISubscribeToAddedToContactsEvent, self).__init__(contact_owner)
        self.contact = contact_added


class PresenceChangedUserNotificationEvent(UserNotificationEvent):
    """
    Pre-defined type of user notification for a presence change event of an
    individual user.

    This object takes care of constructing the :class:`IPresenceInfo` and the
    proper argument dictionary.
    """

    P_ONLINE = u"Online"
    P_OFFLINE = u"Offline"

    __name__ = 'chat_setPresenceOfUsersTo'

    def __init__(self, targets, sender, new_presence):
        """
        :param string sender: The username whose presence is changing.
        :param string new_presence: One of the constants from this class designating
                the new presence state of the user.
        """
        if new_presence == self.P_ONLINE:
            ptype = u'available'
        else:
            ptype = u'unavailable'

        info = component.createObject(u'PresenceInfo',
                                      type=ptype,
                                      username=sender)
        # Could also use getFactoriesFor to work with IPresenceInfo instead of
        # a name...
        args = {sender: info}
        super(PresenceChangedUserNotificationEvent, self).__init__(self.__name__, targets, args)


class IUserRoomEvent(IObjectEvent):
    object = TextLine(title=u"The user/username")
    room_id = TextLine(title=u"The room id.")


class IUserEnterRoomEvent(IUserRoomEvent):
    """
    Fired when a user enters a room
    """


class IUserExitRoomEvent(IUserRoomEvent):
    """
    Fired when a user exits a room
    """


class UserRoomEvent(ObjectEvent):

    def __init__(self, user, room_id):
        super(UserRoomEvent, self).__init__(user)
        self.room_id = room_id

    @property
    def username(self):
        if isinstance(self.object, six.string_types):
            return self.object
        return self.object.username


@interface.implementer(IUserEnterRoomEvent)
class UserEnterRoomEvent(UserRoomEvent):
    pass


@interface.implementer(IUserExitRoomEvent)
class UserExitRoomEvent(UserRoomEvent):
    pass
