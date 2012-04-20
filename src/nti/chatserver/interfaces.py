#!/usr/bin/env python2.7
"""Interfaces having to do with chat."""

from __future__ import unicode_literals

#pylint: disable=E0213,E0211

from zope import interface
from zope.interface import interfaces as z_interfaces
from zope.interface import Interface
from zope import interface
from zope import schema


from nti.dataserver import interfaces as nti_interfaces

class IChatserver(Interface):
	pass

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

class MessageInfoPostedToRoomEvent(MessageInfoEvent):
	interface.implements(IMessageInfoPostedToRoomEvent)

	def __init__( self, obj, recipients=() ):
		super(MessageInfoPostedToRoomEvent,self).__init__( obj )
		self.recipients = recipients

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
