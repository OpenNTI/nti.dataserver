#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Interfaces having to do with chat.

$Id$
"""

from __future__ import unicode_literals, absolute_import, print_function

#pylint: disable=E0213,E0211

from zope import interface
from zope.interface import interfaces as z_interfaces
from zope.interface import Interface
from zope import schema
from zope.security.permission import Permission

from nti.dataserver import interfaces as nti_interfaces
from nti.socketio import interfaces as sio_interfaces

from nti.utils.schema import UniqueIterable
from nti.utils.schema import Variant
from nti.utils.schema import DecodingValidTextLine
TextLine = DecodingValidTextLine
from nti.utils.schema import ValidChoice as Choice
from nti.utils.schema import Object

from nti.contentfragments.schema import PlainTextLine

class IChatserver(Interface):
	pass

class IChatEventHandler(sio_interfaces.ISocketEventHandler):
	"""
	Marker interface for objects designed specifically as chat
	event handlers. These will typically be registered as a multi-adapter
	on the combination ``(user, session, chatserver)``.
	"""

ACT_MODERATE = Permission('nti.chatserver.actions.moderate')
ACT_ENTER = Permission('nti.chatserver.actions.enter')
ACT_ADD_OCCUPANT = Permission('nti.chatserver.actions.add_occupant')

CHANNEL_DEFAULT = 'DEFAULT'
CHANNEL_WHISPER = 'WHISPER'
CHANNEL_CONTENT = 'CONTENT'
CHANNEL_POLL    = 'POLL'
CHANNEL_META    = 'META'
CHANNEL_STATE   = 'STATE'
CHANNELS = (CHANNEL_DEFAULT, CHANNEL_WHISPER, CHANNEL_CONTENT, CHANNEL_POLL, CHANNEL_META, CHANNEL_STATE)

STATUS_INITIAL = 'st_INITIAL'
STATUS_PENDING = 'st_PENDING'
STATUS_POSTED  = 'st_POSTED'
STATUS_SHADOWED = 'st_SHADOWED'
STATUSES = (STATUS_INITIAL,STATUS_PENDING,STATUS_POSTED,STATUS_SHADOWED)


class IMeeting(nti_interfaces.IModeledContent, nti_interfaces.IZContained):
	"""
	Provides the storage structure for a meeting.

    Policy decisions about whether and how to post messages, add/remove occupants
	are delegated to a :class:`IMeetingPolicy` object, which is not expected
	to be persistent and which is created on demand.
	"""

	creator = DecodingValidTextLine( title="Meeting creator", description="User that started the meeting" )

	RoomId = DecodingValidTextLine( title="Meeting identifier", description="Meeting identifier" )

	CreatedTime = schema.Float( title="Meeting creation time",
							 	description="Meeting creation time" )

	Moderated = schema.Bool( title="Whether the meeting is being moderated or not.",
							 description="Toggling this changes the policy in use." )

	Active = schema.Bool( title="Whether the meeting is currently active" )

	occupant_names = schema.Set( title="A set of the string names of members currently in the meeting; immutable." )

	historical_occupant_names = schema.Set( title="A set of the string names of anyone who has ever been a member of this meeting; immutable." )

class IMeetingShouldChangeModerationStateEvent(interface.interfaces.IObjectEvent):
	"""
	Emitted when the :class:`IMeeting` will be changing moderation state.
	"""

	moderated = schema.Bool( title="Whether the meeting should become moderated" )


@interface.implementer(IMeetingShouldChangeModerationStateEvent)
class MeetingShouldChangeModerationStateEvent(interface.interfaces.ObjectEvent):

	def __init__( self, o, flag ):
		super(MeetingShouldChangeModerationStateEvent,self).__init__( o )
		self.moderated = flag

class IMeetingPolicy(interface.Interface):
	"""
	The policy for posting messages to a room. Typically this will
	be an adapter from an :class:`IMeeting`. Responsible for sending events
	to connected sockets.
	"""

	def post_message( msg_info ):
		"""
		:param msg_info: An :class:`IMessageInfo` object.
		:return: A value that can be interpreted as a boolean, indicating success of posting
			the message. If the value is a number and not a `bool` object, then it is the
			number by which the general message count of the room should be incremented (currently only one).
		"""

	def add_moderator( mod_name ):
		"""
		Add a moderator to the room.
		If a moderator was added, emits an event across the sockets of all connected
		users.
		"""

	def approve_message( msg_id ):
		"""
		Optional; raises an error if not supported.
		"""

	def shadow_user( username ):
		"""
		Cause future messages to the user specified by `username` to be copied
		to the moderators of this room.
		:return: Boolean value indicating whether the username was shadowed.
		"""

	moderated_by_usernames = interface.Attribute( "Iterable of names moderating this meeting." )

class IMessageInfo(nti_interfaces.IShareableModeledContent, nti_interfaces.IZContained):
	# We have to be IShareableModeledContent if we want the same ACL provider to work for us
	# as works for Notes
	channel = Choice(
		title="The channel the message was sent to.",
		values=CHANNELS )

	Status = Choice(
		title="The status of the message. Set by the server.",
		values=STATUSES )

	Creator = DecodingValidTextLine( title="Message creator", description="User that send this message" )

	body = Variant( (schema.Dict( key_type=TextLine() ), #, value_type=schema.TextLine() ),
					 nti_interfaces.CompoundModeledContentBody()),
					 description="The body is either a dictionary of string keys and values, or a Note body")

	recipients = UniqueIterable(
		title="The names of all the recipients of the message.",
		description="""The actual recipients of the message, whether or not they are
			named in the message itself. Includes people who just get the transcript.""",
		value_type=TextLine() )


class IMessageInfoEvent(z_interfaces.IObjectEvent):
	"""
	An event having to do with an :class:`IMessageInfo`.
	"""

@interface.implementer( IMessageInfoEvent )
class MessageInfoEvent(z_interfaces.ObjectEvent):
	pass

class IMessageInfoPostedToRoomEvent(IMessageInfoEvent):
	"""
	A message has been delivered to a room.
	"""

	recipients = schema.Set(
		title="The names of all the recipients of the message.",
		description="""The actual recipients of the message, whether or not they are
			named in the message itself. Includes people who just get the transcript.""",
		value_type=schema.TextLine() )

	room = Object(IMeeting,
		title="The room that the message was posted to" )


@interface.implementer( IMessageInfoPostedToRoomEvent )
class MessageInfoPostedToRoomEvent(MessageInfoEvent):

	def __init__( self, obj, recipients, room ):
		super(MessageInfoPostedToRoomEvent,self).__init__( obj )
		self.recipients = recipients
		self.room = room

class IMeetingContainer(Interface):

	def create_meeting_from_dict( chatserver, meeting_dict, constructor ):
		"""
		Called to create (or return) a meeting instance within this container.
		Typically, security will be based on the creator being allowed
		to create a meeting.
		:param chatserver: The chatserver.
		:param Mapping meeting_dict: The description of the room. You may modify
			this. If it has an 'Occupants' key, it will be an iterable of usernames or
			(username, sid) tuples.
		"""


	def meeting_became_empty( chatserver, meeting ):
		"""
		Called to notify that all occupants have left the meeting. The
		meeting will be declared inactive and deleted from
		the chatserver. It may be reactivated by this method, in which case
		it will not be deleted from the chatserver.
		"""


	def enter_active_meeting( chatserver, meeting_dict ):
		"""
		Called when someone wants to enter an active room (if there is one).
		Typically, security will be based on the creator being allowed to occupy the
		meeting.
		:param meeting_dict: Guaranteed to have at least the Creator.
			May be modified. If this method fails (returns None), our caller may call :meth:create_meeting_from_dict
			with this same dictionary.
		:return: The active room, if successfully entered, otherwise None.
		"""

	def create_or_enter_meeting( chatserver, meeting_dict, constructor ):
		"""
		The combination of :meth:`create_or_enter_meeting` with :meth:`enter_active_meeting`.
		If an active meeting exists and the ``Creator`` is allowed to occupy it,
		then it will be returned. Otherwise, if the ``Creator`` is allowed to create
		one then it will be returned.
		:return: A tuple (meeting or None, created). If the first param is not None, the second
			param will say whether it was already active (False) or freshly created (True).
		"""


class IMeetingStorage(Interface):
	"""
	An object for the storage of meetings. The general
	contract is that meetings will be added to this object when
	they are created, and when they become unactive, they will
	be deleted. (However, a storage instance is allowed to let
	the room's lifetime extend beyond that).
	"""

	def get(room_id):
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
		:func:`nti.externalization.oids.to_external_ntiid_oid` (or,
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

class IMessageInfoStorage(Interface):
	"""
	Something that can persistently store chat messages that are
	being sent.
	Ideally, there will be an adapter registered to connect messages
	to users and hang the messages off of the user.
	"""

	def add_message( msg_info ):
		"""
		Cause the message to be stored. Typically, this will
		be done using a :class:`zope.container.interfaces.IContainer`
		and so events will be emitted and ``intids``  will be assigned.
		"""

class IUserTranscriptStorage(Interface):
	"""
	An object that knows how to store transcripts for users
	in a meeting.
	"""

	def transcript_for_meeting( meeting_id ): pass

	def add_message( meeting, msg ): pass

# Presence

class IPresenceInfo(nti_interfaces.ILastModified):
	"""
	A description of the chat presence for a particular user.
	"""
	username = TextLine( title="The global username to which this presence applies.",
						 description="If set when reading from external, may be ignored and replaced with canonical value.",
						 required=False )

	type = Choice( title="What kind of presence this describes",
				   values=('available', 'unavailable'),
				   default='available',
				   required=True)
	show = Choice( title="A hint of how the UI should present the user",
				   values=('away', 'chat', 'dnd', 'xa'),
				   default='chat',
				   required=False )
	status = PlainTextLine( title="Optional plain text status information",
							required=False,
							max_length=140 )

	def isAvailable():
		"""Does the presence represent a user who is available for chat/chat APIs?"""

class IContacts(Interface):
	"""
	Something that can report on the "friends" or "buddy list" or "contact list"
	of a particular entity. This may or may not be persistent and editable
	by the entity (it may be derived from other information). This is intended
	to be used by adapting the entity to this interface.
	"""

	__parent__ = Object( nti_interfaces.IUser, title="The owner of this contact list" )

	contactNamesSubscribedToMyPresenceUpdates = UniqueIterable( title="The usernames of buddies that should get updates when the owner's presence changes",
																description="Probably computed as a property",
																value_type=TextLine(title="A username" ) )

	contactNamesISubscribeToPresenceUpdates =  UniqueIterable( title="The usernames of buddies that the owner wants presence updates for",
															   description="Probably computed as a property",
															   value_type=TextLine(title="A username" ) )



class PresenceChangedUserNotificationEvent(nti_interfaces.UserNotificationEvent):
	"""
	Pre-defined type of user notification for a presence change event.
	"""

	P_ONLINE  = "Online"
	P_OFFLINE = "Offline"

	def __init__( self, targets, sender, new_presence ):
		"""
		:param string sender: The username whose presence is changing.
		:param string new_presence: One of the constants from this class designating
			the new presence state of the user.
		"""
		super(PresenceChangedUserNotificationEvent,self).__init__( "chat_presenceOfUserChangedTo",
																   targets,
																   sender,
																   new_presence )
