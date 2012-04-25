#!/usr/bin/env python
""" Chatserver functionality. """
from __future__ import print_function, unicode_literals
__docformat__ = "restructuredtext en"

import logging
logger = logging.getLogger( __name__ )


import numbers
import UserDict

from nti.externalization.externalization import toExternalObject
from nti.externalization import oids
from nti.externalization.interfaces import StandardExternalFields as XFields

from nti.dataserver.activitystream_change import Change
from nti.dataserver.activitystream import enqueue_change
from nti.dataserver import users
from nti.dataserver import interfaces as nti_interfaces


from persistent import Persistent
from persistent.mapping import PersistentMapping


from zope import interface
from zope import component
from zope.deprecation import deprecate, deprecated
from zope import minmax

from . import interfaces
from ._handler import ChatHandlerFactory
from .meeting import _Meeting

class _AlwaysIn(object):
	"""Everything is `in` this class."""
	def __init__(self): pass
	def __contains__(self,obj): return True

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


EVT_ENTERED_ROOM = 'chat_enteredRoom'
EVT_EXITED_ROOM = 'chat_exitedRoom'
EVT_POST_MESSOGE = 'chat_postMessage'
EVT_RECV_MESSAGE = 'chat_recvMessage'



class PersistentMappingMeetingStorage(Persistent):
	"""
	An implementation of :class:`chat_interfaces.IMeetingStorage` using
	some sort of persistent mapping. The default is in fact
	:class:`PersistentMapping`, but this may be changed at construction.
	"""
	interface.implements(interfaces.IMeetingStorage)

	def __init__( self, mapping_factory=PersistentMapping ):
		self.meetings = mapping_factory()

	def __delitem__( self, room_id ):
		del self.meetings[room_id]

	def __getitem__( self, room_id ):
		return self.meetings[room_id]

	def add_room( self, room ):
		if getattr( self, '_p_jar', None ) \
			and getattr( room, '_p_jar', self ) is None:
			getattr( self, '_p_jar' ).add( room )

		room.id = oids.to_external_ntiid_oid( room, None )

		if room.id is None:
			raise ValueError( "Unable to assign ID, not persistent" )
		self.meetings[room.id] = room

	def get( self, room_id ):
		return self.meetings.get( room_id )



class Chatserver(object):
	""" Collection of all the state related to the chatserver, including active rooms, etc. """

	interface.implements( interfaces.IChatserver )

	def __init__( self,
				  user_sessions,
				  meeting_storage=None,
				  meeting_container_storage=None ):
		"""
		Create a chatserver.

		:param user_sessions: Supports :meth:`get_session` for session_id and :meth:`get_sessions_by_owner` for
			getting all sessions for a given user. A session has a `protocol_handler` attribute
			which has a `send_event` method.
		:param meeting_storage: Storage for meeting instances, supports get, __getitem__, and __delitem__. If not
			given, we use a dictionary.
		:param Mapping meeting_container_storage: Read-only dictionary used to look up containers
			of meetings. If the result is a :class:`IMeetingContainer`, it will be called to create the room.

		"""
		super(Chatserver,self).__init__()
		self.sessions = user_sessions
		# Mapping from room id to room.
		self.rooms = meeting_storage \
					 if meeting_storage is not None \
					 else PersistentMappingMeetingStorage()
		self.meeting_container_storage = meeting_container_storage \
										 if meeting_container_storage is not None \
										 else PersistentMapping()

	def __reduce__(self):
		raise TypeError()

	### Sessions

	def get_session_for( self, session_owner_name, session_ids=_AlwaysIn() ):
		"""
		:return: Session for the given owner.
		:param session_owner_name: The session.owner to match.
		:param session_ids: If not None, the session's ID must also match.
			May be a single session ID or something that supports 'in.'
		"""
		if session_ids is None:
			session_ids = _AlwaysIn()
		elif not isinstance(session_ids,_AlwaysIn) and isinstance(session_ids, (basestring,numbers.Number)):
			# They gave us a bare string
			session_ids = (session_ids,)
		# Since this is arbitrary by name, we choose to return
		# the most recently created session that matches.
		candidates = list( self.sessions.get_sessions_by_owner( session_owner_name ) )
		candidates.sort( key=lambda x: x.creation_time, reverse=True )
		for s in candidates:
			if s.session_id in session_ids:
				return s
		return None

	### Low-level IO

	def send_event_to_user( self, username, name, *args ):
		"""
		Directs the event named ``name`` to all sessions for the ``username``.
		The sequence of ``args`` is externalized and send with the event.
		"""
		if username:
			all_sessions = self.sessions.get_sessions_by_owner( username )
			if not all_sessions: # pragma: no cover
				logger.debug( "No sessions for %s to send event %s to", username, name )
				return
			args = [toExternalObject( arg ) for arg in args]
			for s in all_sessions:
				logger.debug( "Dispatching %s to %s", name, s )
				s.socket.send_event( name, *args )

	### Rooms

	def post_message_to_room( self, room_id, msg_info ):
		room = self.rooms.get( room_id )
		if room is None or not room.Active:
			logger.info( "Dropping message to non-existant/inactive room '%s' '%s'", room_id, room )
			return False
		# Right now, there is no valid use case for the sender to
		# send a message only to himself. Right now, there's also
		# not a good way to signal this as an error so we silently drop it
		if len(msg_info.recipients) == 1 and not msg_info.recipients_without_sender:
			logger.info( "Dropping message only to the sender in room %s", room )
			return False
		# To post a message to a room, you must be an occupant
		if msg_info.Sender not in room.occupant_session_names:
			logger.info( "Dropping message from an occupant not in the room %s %s", room, msg_info )
			return False
		return room.post_message( msg_info )


	def enter_meeting_in_container( self, room_info_dict ):
		"""
		:param dict room_info_dict: A dict similar to the one given to :meth:`create_room_from_dict`.
			MUST have a ContainerID, which resolves to an :class:IMeetingContainer. Must
			have one value in the sequence for the Occupants key, the tuple of (sender,sid).
		:return: The room entered, or None.
		"""
		# TODO: This is racy.
		container = self.meeting_container_storage.get( room_info_dict[XFields.CONTAINER_ID] )
		if not hasattr( container, 'enter_active_meeting' ):
			# The container didn't match any storage.
			logger.info( "The requested container (%s) (info: %s) is not a persistent meeting room; not entering", container, room_info_dict )
			return None

		# At this point, we know we have exactly one Occupant, the (sender,sid).
		# This next call MIGHT change that, so preserve it.
		occupant_tuple = room_info_dict['Occupants'][0]
		room = container.enter_active_meeting( self, room_info_dict )
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
			logger.debug( "%s entering existing persistent meeting %s", occupant_tuple, room )
			# Yes, we got in. Announce this.
			room.add_occupant_name( occupant_tuple[0] )
		else:
			# We didn't get in. We know we have a container, though,
			# so see if we can start one.
			logger.debug( "%s creating new persistent meeting %s", occupant_tuple, room_info_dict )
			room = self.create_room_from_dict( room_info_dict )
		return room

	def create_room_from_dict( self, room_info_dict, sessions_validator=None ):
		"""
		Creates a room given a dictionary of values.

		:param dict room_info_dict: Contains at least an `Occupants` key. This key
			is an iterable of usernames or (username,session_id) tuples.
		:param function sessions_validator: If given, a callable of one argument, a sequence of sessions.
			Returns whether or not to allow the room creation given those sessions.
		"""

		room_info_dict = dict( room_info_dict ) # copy because we will modify

		# We need to resolve names into sessions, whether or not there
		# is a container, so we do it now.

		room = None
		# If the container is specified, and is found as something
		# that wants to have a say, let it.
		if XFields.CONTAINER_ID in room_info_dict:
			container = self.meeting_container_storage.get( room_info_dict[XFields.CONTAINER_ID] )
			if hasattr( container, 'create_or_enter_meeting' ):
				# The container will decide what to do with things like
				# Occupants, they may ignore it or replace it entirely.
				orig_occupants = list(room_info_dict['Occupants'])
				room, created = container.create_or_enter_meeting( self, room_info_dict, lambda: _Meeting(self) )
				if room is None or not room.Active:
					logger.debug( "Container %s vetoed creation of room %s (%s)",
								  container, room, room_info_dict )
					# The container vetoed creation for some reason.
					return None
				if room is not None and not created:
					# We got back an already active room that we should enter.
					# Check for our session and make sure we're in the room (just like enter_meeting_in_container)
					logger.debug( 'Container %s found an existing room %s and forced us into it %s',
								  container, room, room_info_dict )
					for orig_occupant in orig_occupants:
						if isinstance( orig_occupant, tuple ) and orig_occupant[0] == room_info_dict['Creator']:
							room.add_occupant_name( orig_occupant[0] )
							break
					return room

				# Containers deal with, roughly, persistent rooms. Therefore, if they
				# give us a list of occupants, then regardless of whether
				# they are currently online these occupants should get transcripts.
				for occupant in room_info_dict['Occupants']:
					if isinstance( occupant, tuple ): occupant = occupant[0]
					room.add_additional_transcript_username( occupant )

		if room is None:
			room = _Meeting(self)

		# Resolve occupants, chiefly to make sure some are online
		sessions = []
		occupants = []
		for occupant in room_info_dict['Occupants']:
			session = None
			session_ids = None
			if isinstance( occupant, tuple ):
				# Two-tuples give us the session ID
				session_ids = occupant[1]
				occupant = occupant[0]
			occupants.append( occupant )
			session = self.get_session_for( occupant, session_ids )
			if session:	sessions.append( session.session_id )
		if not sessions or (callable(sessions_validator) and not sessions_validator(sessions)):
			logger.debug( "No occupants found for room %s", room_info_dict )
			return None
		# Run it through the usual dict-to-object mechanism
		# so that we get correct OID resolution
		room_info_dict.pop( 'Occupants' )
		room_info_dict.pop( 'Active', None )
		component.getUtility( nti_interfaces.IDataserver ).update_from_external_object( room, room_info_dict )
		# Make sure the room is all setup before
		# we add the sessions, since that will broadcast
		# events using the room's info
		room.Active = True
		# FIXME: For storage to work out correctly, the creator
		# must not be set when the ID is assigned. (What?) Otherwise
		# transcripts cannot be found and a test fails. This then causes
		# a mismatch between the 'creator' and the value in the 'NTIID'/'id', so
		# everyone must use get_by_oid(ignore_creator=True), which is bad.
		self.rooms.add_room( room )
		if not room.creator: # The storage may have set this already, don't override
			room.creator = room_info_dict['Creator']

		room.add_occupant_names( occupants )
		return room

	def get_meeting( self, room_id ):
		return self.rooms.get( room_id )

	def exit_meeting( self, room_id, username ):
		"""
		:return: Value indicating successful exit.
		"""
		result = None
		room = self.rooms.get( room_id )
		if room:
			result = room.del_occupant_name( username )
			if not room.occupant_names:
				room.Active = False
				container = self.meeting_container_storage.get( room.containerId )
				if hasattr( container, 'meeting_became_empty' ):
					container.meeting_became_empty( self, room )

				# We do not have the concept of persistent
				# meetings, merely persistent meeting containers.
				# Transcripts keep their own references to meetings,
				# so when a meeting becomes empty, we are free
				# to clear our reference to it.
				if not room.Active:
					del self.rooms[room_id]
		return result

	### Transcripts

	def _ts_storage_for( self, owner, create_if_missing=True ):
		storage = None
		if owner:
			# TODO: Need a component to resolve users
			user = users.User.get_user( owner )
			storage = component.queryAdapter( user, interfaces.IUserTranscriptStorage ) \
					if user \
					else None
		return storage

	def _save_message_to_transcripts( self, msg_info, transcript_names, transcript_owners=() ):
		"""
		Adds the message to the transcripts of each user given.

		:param MessageInfo msg_info: The message. Must have a container id.
		:param iterable transcript_names: Iterable of usernames to post the message to.
		:param iterable transcript_owners: Iterable of usernames to post the message to.
		"""
		owners = set( transcript_owners )
		owners.update( set(transcript_names) )

		change = Change( Change.CREATED, msg_info )
		change.creator = msg_info.Sender

		meeting = self.rooms.get( msg_info.containerId )
		for owner in owners:
			storage = self._ts_storage_for( owner )
			storage.add_message( meeting, msg_info )

			enqueue_change( change, username=owner, broadcast=True )

	def transcript_for_user_in_room( self, username, room_id ):
		"""
		Returns a :class:`Transcript` for the user in room.
		If the user wasn't in the room, returns None.
		"""
		result = None
		storage = self._ts_storage_for( username, create_if_missing=False )
		if storage:
			result = storage.transcript_for_meeting( room_id )
		return result

	def transcript_summaries_for_user_in_container( self, username, containerId ):
		"""

		:return: Map of room/transcript id to :class:`TranscriptSummary` objects for the user that
			have taken place in the given containerId. The map will have attributes `lastModified`
			and `creator`.

		EOM
		"""
		storage = self._ts_storage_for( username, create_if_missing=False )
		if not storage:
			return dict()

		data = {summary.RoomInfo.ID: summary
				for summary
				in storage.transcript_summaries
				if summary.RoomInfo.containerId == containerId}
		logger.debug( "All summaries %s", data )
		result = UserDict.UserDict( data )
		result.creator = username
		if data:
			result.lastModified = max( data.itervalues(), key=lambda x: x.LastModified ).LastModified
		return result

	def list_transcripts_for_user( self, username ):
		"""
		Returns an Iterable of :class:`TranscriptSummary` objects for the user.
		"""
		storage = self._ts_storage_for( username, create_if_missing=False )
		if not storage:
			return ()
		return storage.transcript_summaries


@component.adapter( interfaces.IMessageInfo, interfaces.IMessageInfoPostedToRoomEvent )
def _save_message_to_transcripts_subscriber( msg_info, event ):
	"""
	Event handler that saves messages to the appropriate transcripts.
	"""
	chatserver = component.queryUtility( interfaces.IChatserver )
	if chatserver:
		chatserver._save_message_to_transcripts( msg_info, event.recipients )

@component.adapter(interfaces.IUserNotificationEvent)
def _send_notification( user_notification_event ):
	"""
	Event handler that sends notifications to connected users.
	"""
	chatserver = component.queryUtility( interfaces.IChatserver )
	if chatserver:
		for target in user_notification_event.targets:
			try:
				chatserver.send_event_to_user( target, user_notification_event.name, *user_notification_event.args )
			except AttributeError: # pragma: no cover
				raise
			except Exception: # pragma: no cover
				logger.exception( "Failed to send %s to %s", user_notification_event, target )
