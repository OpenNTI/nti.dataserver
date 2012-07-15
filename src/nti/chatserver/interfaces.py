#!/usr/bin/env python2.7
"""Interfaces having to do with chat."""

from __future__ import unicode_literals

#pylint: disable=E0213,E0211

from zope import interface
from zope.interface import interfaces as z_interfaces
from zope.interface import Interface
from zope import schema
from zope.security.permission import Permission

from nti.dataserver import interfaces as nti_interfaces

class IChatserver(Interface):
	pass

ACT_MODERATE = Permission('nti.chatserver.actions.moderate')

CHANNEL_DEFAULT = 'DEFAULT'
CHANNEL_WHISPER = 'WHISPER'
CHANNEL_CONTENT = 'CONTENT'
CHANNEL_POLL    = 'POLL'
CHANNEL_META    = 'META'
CHANNELS = (CHANNEL_DEFAULT, CHANNEL_WHISPER, CHANNEL_CONTENT, CHANNEL_POLL, CHANNEL_META)
CHANNEL_VOCABULARY = schema.vocabulary.SimpleVocabulary(
	[schema.vocabulary.SimpleTerm( _x ) for _x in CHANNELS] )

STATUS_INITIAL = 'st_INITIAL'
STATUS_PENDING = 'st_PENDING'
STATUS_POSTED  = 'st_POSTED'
STATUS_SHADOWED = 'st_SHADOWED'
STATUSES = (STATUS_INITIAL,STATUS_PENDING,STATUS_POSTED,STATUS_SHADOWED)
STATUS_VOCABULARY = schema.vocabulary.SimpleVocabulary(
	[schema.vocabulary.SimpleTerm( _x ) for _x in STATUSES] )

class IMeeting(nti_interfaces.IModeledContent):
	"""
	Provides the storage structure for a meeting.

    Policy decisions about whether and how to post messages, add/remove occupants
	are delegated to a :class:`IMeetingPolicy` object, which is not expected
	to be persistent and which is created on demand.
	"""

	Moderated = schema.Bool( title="Whether the meeting is being moderated or not.",
							 description="Toggling this changes the policy in use." )

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

class IMessageInfo(nti_interfaces.IModeledContent):

	channel = schema.Choice(
		title="The channel the message was sent to.",
		vocabulary=CHANNEL_VOCABULARY)
	Status = schema.Choice(
		title="The status of the message. Set by the server.",
		vocabulary=STATUS_VOCABULARY )

class IMessageInfoEvent(z_interfaces.IObjectEvent):
	"""
	An event having to do with an :class:`IMessageInfo`.
	"""

class MessageInfoEvent(z_interfaces.ObjectEvent):
	interface.implements(IMessageInfoEvent)


class IMessageInfoPostedToRoomEvent(IMessageInfoEvent):
	"""
	A message has been delivered to a room.
	"""

	recipients = schema.Set(
		title="The names of all the recipients of the message.",
		description="""The actual recipients of the message, whether or not they are
			named in the message itself. Includes people who just get the transcript.""",
		value_type=schema.TextLine() )

	room = schema.Object(IMeeting,
		title="The room that the message was posted to" )


class MessageInfoPostedToRoomEvent(MessageInfoEvent):
	interface.implements(IMessageInfoPostedToRoomEvent)

	def __init__( self, obj, recipients=(), room=None ):
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
	An object for the temporary shared storage of meetings
	that are active.
	"""

	def get(room_id):
		"""
		Returns the stored room having the given ID, or None
		if there is no room with that Id stored in this object.
		"""

	def __getitem__(room_id):
		"""
		Returns the stored room with that ID or raises KeyError.
		"""

	def add_room(room):
		"""
		Stores a room in this object. Sets the room's (an IContained)
		`id` property to be in the form produced by :func:`datatstructures.to_external_ntiid_oid`.
		"""

	def __delitem__(room_id):
		"""
		Removes the room stored in this object with the given id or
		raises KeyError.
		"""

class IUserTranscriptStorage(Interface):
	"""
	An object that knows how to store transcripts for users
	in a meeting.
	"""

	def transcript_for_meeting( meeting_id ): pass

	def add_message( meeting, msg ): pass


class IUserNotificationEvent(Interface):
	"""
	An event that is emitted with the intent of resulting in
	a notification to one or more end users.

	The chatserver will not produce these events, but it will listen
	for them and attempt to deliver them to the connected target users.
	"""

	targets = schema.Iterable( title="Iterable of usernames to attempt delivery to." )
	name = schema.TextLine(	title="The name of the event to deliver" )
	args = schema.Iterable( title="Iterable of objects to externalize and send as arguments." )


class UserNotificationEvent(object):
	"Base class for user notification events"
	interface.implements(IUserNotificationEvent)

	def __init__( self, name, targets, *args ):
		self.name = name
		self.targets = targets
		self.args = args

class PresenceChangedUserNotificationEvent(UserNotificationEvent):
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

class DataChangedUserNotificationEvent(UserNotificationEvent):
	"""
	Pre-defined type of user notification for a change in data.
	"""

	def __init__( self, targets, change ):
		"""
		:param change: An object representing the change.
		"""
		super(DataChangedUserNotificationEvent,self).__init__( "data_noticeIncomingChange", targets, change )
