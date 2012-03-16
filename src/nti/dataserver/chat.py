""" Chatserver functionality. """

__docformat__ = "restructuredtext en"

import logging
logger = logging.getLogger( __name__ )

import time
import uuid
import collections
import numbers
import six
import warnings

import datastructures
from datastructures import StandardExternalFields as XFields

import ntiids
from activitystream_change import Change
from activitystream import enqueue_change
from nti.dataserver import chat_interfaces
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver import users
from nti.dataserver import contenttypes

import persistent
from persistent import Persistent
from persistent.mapping import PersistentMapping
import BTrees.OOBTree

from zope import interface
from zope import component
from zope.deprecation import deprecate, deprecated


class _AlwaysIn(object):
	"""Everything is `in` this class."""
	def __init__(self): pass
	def __contains__(self,obj): return True

CHANNEL_DEFAULT = 'DEFAULT'
CHANNEL_WHISPER = 'WHISPER'
CHANNEL_CONTENT = 'CONTENT'
CHANNEL_POLL    = 'POLL'
CHANNEL_META    = 'META'
CHANNELS = (CHANNEL_DEFAULT, CHANNEL_WHISPER, CHANNEL_CONTENT, CHANNEL_POLL, CHANNEL_META)

STATUS_INITIAL = 'st_INITIAL'
STATUS_PENDING = 'st_PENDING'
STATUS_POSTED  = 'st_POSTED'
STATUS_SHADOWED = 'st_SHADOWED'

class MessageInfo( contenttypes.ThreadableExternalizableMixin,
				   Persistent,
				   datastructures.ExternalizableInstanceDict ):

	__external_can_create__ = True

	_excluded_in_ivars_ = { 'MessageId' } | datastructures.ExternalizableInstanceDict._excluded_in_ivars_

	_prefer_oid_ = False

	# The usernames of occupants of the initial room, and others
	# the transcript should go to. Set by policy.
	sharedWith = ()

	def __init__( self ):
		super(MessageInfo,self).__init__()
		self.ID = uuid.uuid4().hex
		self.Creator = None # aka Sender. Forcibly set by the handler
		self._v_sender_sid = None # volatile. The session id of the sender.
		self.LastModified = time.time()
		self.CreatedTime = self.LastModified
		self.containerId = None
		self.channel = CHANNEL_DEFAULT
		self.body = None
		self.recipients = ()
		self.Status = STATUS_INITIAL

	def get_Sender(self):
		return self.Creator
	def set_Sender(self,s):
		self.Creator = s
	Sender = property( get_Sender, set_Sender )


	def get_sender_sid( self ):
		"""
		When this message first arrives, this will
		be the session id of the session that sent
		the message. After that, it will be None.
		"""
		return getattr( self, '_v_sender_sid', None )
	def set_sender_sid( self, sid ):
		setattr( self, '_v_sender_sid', sid )
	sender_sid = property( get_sender_sid, set_sender_sid )

	# Aliases for old code
	@property
	def MessageId( self ):
		return self.ID

	@property
	def Timestamp(self):
		return self.LastModified

	@property
	def rooms( self ):
		return [self.containerId]

	def get_Body( self ):
		return self.body
	def set_Body( self, body ):
		self.body = body
	Body = property( get_Body, set_Body )

	@property
	def recipients_without_sender(self):
		"""
		All the recipients of this message, excluding the Sender.
		"""
		recip = set( self.recipients )
		recip.discard( self.Sender )
		return recip

	@property
	def recipients_with_sender( self ):
		"""
		All the recipients of this message, including the Sender.
		"""
		recip = set( self.recipients )
		recip.add( self.Sender )
		return recip

	def is_default_channel( self ):
		return self.channel is None or self.channel == CHANNEL_DEFAULT

	def toExternalDictionary( self, mergeFrom=None ):
		result = super(MessageInfo,self).toExternalDictionary( mergeFrom=mergeFrom )
		if self.body is not None:
			# alias for old code.
			result['Body'] = result['body']
		return result

	def updateFromExternalObject( self, parsed, *args, **kwargs ):
		super(MessageInfo,self).updateFromExternalObject( parsed, *args, **kwargs )
		if 'Body' in parsed and 'body' not in parsed:
			self.body = parsed['Body']
		if 'Body' or 'body' in parsed:
			if isinstance( self.body, six.string_types ):
				self.body = contenttypes.sanitize_user_html( self.body )
			elif isinstance( self.body, collections.Sequence ):
				self.body = [contenttypes.sanitize_user_html( x ) if isinstance(x,six.string_types) else x
							 for x
							 in self.body]

	def __setstate__( self, state ):
		# Migration
		body = self
		if 'Body' in state:
			body = state.pop( 'Body' )
		super(MessageInfo,self).__setstate__( state )
		if body is not self:
			self.body = body

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


def _send_event( chatserver, sessions, name, *args ):
	"""
	Utility method to send an event to a session or sessions.
	"""
	if isinstance( sessions, basestring) or not isinstance( sessions, collections.Iterable ):
		sessions = (sessions,)
	for session in sessions:
		chatserver.send_event( session, name, *args )

class _ChatObjectMeta(type):

	def __new__( mcs, clsname, clsbases, clsdict ):
		if '__emits__' not in clsdict:
			return type.__new__( mcs, clsname, clsbases, clsdict )

		def make_emit(signal):
			return lambda s, sessions, *args: _send_event( s._chatserver, sessions, signal, *args )
		for signal in (clsdict['__emits__']):

			clsdict['emit_' + signal] = make_emit( signal if '_' in signal else 'chat_' + signal )

		return type.__new__( mcs, clsname, clsbases, clsdict )

def _discard( s, k ):
	if hasattr( s, 'discard' ):
		s.discard(k)
	else:
		try:
			s.remove( k )
		except KeyError: pass
		except ValueError: pass
		except AttributeError: pass

class _ChatHandler( Persistent ):
	"""
	Class to handle each of the messages sent to or from a client.

	Instances of this class are tied to the session, not the chatserver.
	They should go away when the user's session does.
	"""

	__metaclass__ = _ChatObjectMeta
	__emits__ = ('recvMessageForAttention', 'presenceOfUserChangedTo',
				 'data_noticeIncomingChange', 'failedToEnterRoom' )

	interface.implements(nti_interfaces.ISocketEventHandler)
	event_prefix = 'chat'
	# public methods correspond to events

	def __init__( self, chatserver, session ):
		""" """
		self._chatserver = chatserver
		self.session_id = session.session_id
		self.session_owner = session.owner
		self.rooms_i_moderate = PersistentMapping()
		self.rooms_im_in = BTrees.OOBTree.Set()

	def __str__( self ):
		return "%s(%s %s)" % (self.__class__.__name__, self.session_owner, self.session_id)

	def postMessage( self, msg_info ):
		# Ensure that the sender correctly matches.
		msg_info.Sender = self.session_owner
		msg_info.sender_sid = self.session_id
		result = True
		for room in set(msg_info.rooms):
			result &= self._chatserver.post_message_to_room( room, msg_info )
		return result

	def enterRoom( self, room_info ):
		room = None
		room_info['Creator'] = self.session_owner
		if room_info.get( 'RoomId' ) is not None:
			# Trying to join an established room
			# Right now, unsupported.
			logger.debug( "Cannot enter existing room %s", room_info )
		elif len( room_info.get( 'Occupants', () ) ) == 0 and XFields.CONTAINER_ID in room_info:
			# No occupants, but a container ID. This must be for something
			# that can persistently host meetings. We want
			# to either create or join it.
			room_info['Occupants'] = [ (self.session_owner, self.session_id ) ]
			room = self._chatserver.enter_meeting_in_container( room_info )
		else:
			# Creating a room to chat with. Make sure I'm in it.
			# More than that, make sure it's my session, and any
			# of my friends lists are expanded
			_discard( room_info.get('Occupants'), self.session_owner )
			room_info['Occupants'] = list( room_info['Occupants'] )
			user = users.User.get_user( self.session_owner )
			if user:
				for i in list(room_info['Occupants']):
					if i in user.friendsLists:
						room_info['Occupants'] += [x.username for x in user.friendsLists[i]]
			room_info['Occupants'].append( (self.session_owner, self.session_id) )
			room = self._chatserver.create_room_from_dict( room_info )

		if room:
			self.rooms_im_in.add( room.RoomId )
		else:
			self.emit_failedToEnterRoom( self.session_id, room_info )
		return room

	def exitRoom( self, room_id ):
		result = self._chatserver.exit_meeting( room_id, self.session_id )
		_discard( self.rooms_im_in, room_id )
		return result

	def makeModerated( self, room_id, flag ):
		# TODO: Roles. Who can moderate?
		room = self._chatserver.get_meeting( room_id )
		if room and flag != room.Moderated:
			room.Moderated = flag
			if flag:
				logger.debug( "%s becoming moderator of room %s", self, room )
				room.add_moderator( self.session_id )
				self.rooms_i_moderate[room.RoomId] = room
			else:
				self.rooms_i_moderate.pop( room.RoomId, None )
		else:
			logger.debug( "%s Not changing moderation status of %s (%s) to %s",
						  self, room, room_id, flag )
		return room

	def approveMessages( self, m_ids ):
		for m in m_ids:
			for room in self.rooms_i_moderate.itervalues():
				room.approve_message( m )

	def flagMessagesToUsers( self, m_ids, usernames ):
		# TODO: Roles again. Who can flag to whom?
		warnings.warn( "Allowing anyone to flag messages to users." )
		user_sessions = [self._chatserver.get_session_for( username )
						 for username
						 in usernames]
		warnings.warn( "Assuming that clients have seen messages flagged to them." )
		for m in m_ids:
			# TODO: Where does this state belong? Who
			# keeps the message? Passing just the ID assumes
			# that the client can find the message by id.
			self.emit_recvMessageForAttention( user_sessions, m )
		return True

	def shadowUsers( self, room_id, usernames ):
		room = self._chatserver.get_meeting( room_id )
		# TODO: Roles.
		warnings.warn( "Allowing anyone to activate shadowing." )
		result = False
		if room and room.Moderated:
			result = True
			for user in usernames:
				result &= room.shadowUser( user )
		return result

	def destroy( self ):
		for room_in in set( self.rooms_im_in ):
			self.exitRoom( room_in )


class _Meeting(contenttypes.ThreadableExternalizableMixin,
				Persistent,
				datastructures.ExternalizableInstanceDict):
	"""Class to handle distributing messages to clients. """

	__metaclass__ = _ChatObjectMeta
	__emits__ = ('recvMessage', 'enteredRoom', 'exitedRoom',
				 'roomMembershipChanged' )
	_prefer_oid_ = False

	# Should probably have subclasses for moderation and the like?

	def __init__( self, chatserver ):
		super(_Meeting,self).__init__()
		self._chatserver = chatserver
		self.Active = True
		self.id = None
		self.containerId = None
		self.MessageCount = 0
		self.CreatedTime = time.time()
		self._occupant_session_ids = BTrees.OOBTree.Set()
		# Sometimes a room is created with a subset of the occupants that
		# should receive transcripts. The most notable case of this is
		# creating a room in reply to something that's shared: everyone
		# that it is shared with should get the transcript even if they
		# didn't participate in the room because they were offline.
		# TODO: How does this interact with things that are
		# shared publically and not specific users?
		self._addl_transcripts_to = BTrees.OOBTree.Set()
		# Things for the moderation subclass
		self._moderated = False

	def __setstate__( self, state ):
		super(_Meeting,self).__setstate__( state )
		# Because we are swizzling classes dynamically at
		# runtime, that fact may not be persisted in the database.
		# We have to restore it when the object comes alive.
		# This is tightly coupled with the implementation of
		# _becameModerated/_becameUnmoderated
		if hasattr( self, '_moderation_queue' ) and self.__class__ == _Meeting:
			self.__class__ = _ModeratedMeeting

	def __getattribute__( self, name ):
		result = super(_Meeting,self).__getattribute__( name )
		# Unghost to guarantee we're the right class. We force this
		# if a class attribute that's important to moderation is accessed first,
		# before an instance var that would normally trigger this
		if name == 'post_message' and result and super(_Meeting,self).__getattribute__('_p_state') == persistent.GHOST:
			self._p_activate()
			result = super(_Meeting,self).__getattribute__('post_message')
		return result
	

	@property
	def RoomId(self):
		return self.id
	@property
	def ID(self):
		return self.id

	def _becameModerated(self): pass
	def _becomeUnmoderated(self): pass

	def _Moderated( self ):
		return self._moderated

	def _setModerated( self, flag ):
		if flag != self._moderated:
			self._moderated = flag
			if self._moderated:
				# become moderated.
				self.__class__ = _ModeratedMeeting
				self._becameModerated()
			else:
				#become unmoderated.
				self._becomeUnmoderated()
				self.__class__ = _Meeting

	Moderated = property( _Moderated, _setModerated )
	Moderators = ()
	@property
	def occupant_session_ids(self):
		"""
		:return: A set of all the session ids occupying this room.
		"""
		return frozenset(self._occupant_session_ids)

	def _find_sessions( self, sids ):
		"""
		:return: The sessions of all the active sessions in the given
			iterable of session ids.
		"""
		result = []
		for session_id in sids:
			sess = self._chatserver.get_session( session_id )
			if sess:
				result.append( sess )
		return result

	@property
	def occupant_sessions(self):
		"""
		:return: An iterable of the active sessions for all
			the session ids in this room. Note that this will have length
			equal or less than :meth:`occupant_session_ids` due to inactive
			sessions.
		"""
		return self._find_sessions( self._occupant_session_ids )


	@property
	def occupant_session_names(self):
		"""
		:return: An iterable of the names of all active users in this room.
			See :meth:`occupant_sessions`.
		"""
		return { sess.owner for sess in self.occupant_sessions }

	def _ensure_message_stored( self, msg_info ):
		"""
		For messages that can take an OID, call this
		to ensure that they have one. Must be called
		during a transaction.
		"""
		if getattr( msg_info, '_p_jar' ) is None and self._p_jar:
			self._p_jar.add( msg_info )

	def _treat_recipients_like_default_channel( self, msg_info ):
		return msg_info.is_default_channel() or not msg_info.recipients_without_sender

	def _get_recipient_sessions_for_message( self, msg_info ):
		if self._treat_recipients_like_default_channel( msg_info ):
			recipient_sessions = { self._chatserver.get_session( sid )
								   for sid in self._occupant_session_ids }
		else:
			recipient_sessions = { self._chatserver.get_session_for( r, session_ids=self._occupant_session_ids )
								   for r in msg_info.recipients_with_sender }
		recipient_sessions.discard( None )
		return recipient_sessions

	def _get_recipient_sids_for_message( self, msg_info, recipient_sessions=None ):
		return {s.session_id for s in (recipient_sessions or self._get_recipient_sessions_for_message( msg_info ))}

	def _sids_excluded_when_considering_all( self ):
		"""
		:return: A set of sids excluded when comparing against all occupants.
		"""
		return set()

	def _is_message_to_all_occupants( self, msg_info, recipient_sids=None, recipient_sessions=None ):
		"""
		Should the message be treated as if it were the default
		channel? Yes, if it is either to the DEFAULT channel, an empty recipient list, or its recipient list
		is to everyone (not excluded by :meth:`_sids_excluded_when_considering_all`)
		"""
		if self._treat_recipients_like_default_channel( msg_info ):
			return True
		return (recipient_sids or self._get_recipient_sids_for_message( msg_info, recipient_sessions=recipient_sessions )) \
			   == (set(self._occupant_session_ids) - self._sids_excluded_when_considering_all())

	def _is_message_on_supported_channel( self, msg_info ):
		"""
		Whether the message is on a channel supported by this
		room.
		"""
		return (msg_info.channel or CHANNEL_DEFAULT) in (CHANNEL_DEFAULT, CHANNEL_WHISPER)

	def post_message( self, msg_info ):
		if not self._is_message_on_supported_channel( msg_info ):
			logger.debug( "Dropping message on unsupported channel %s", msg_info )
			return False
		# TODO: How to handle messages from senders that do not occupy this room?
		# In the ordinary case, would we want to drop them?
		# It becomes complicated in the moderated case where there may
		# be a delay involved.
		msg_info.Status = STATUS_POSTED
		# Ensure it's this room, thank you.
		msg_info.containerId = self.ID
		# Ensure there's an OID
		self._ensure_message_stored( msg_info )

		transcript_owners = set(self._addl_transcripts_to)
		transcript_owners.add( msg_info.Sender )

		# Accumulate the session IDs of everyone who should get a copy.
		# Note that may or may not include the sender--hence transcript_owners. (See note above)
		recipient_sessions = self._get_recipient_sessions_for_message( msg_info )

		if self._is_message_to_all_occupants( msg_info, recipient_sessions=recipient_sessions ):
			# recipients are ignored for the default channel,
			# and a message to everyone also counts for incrementing the ids.
			self.MessageCount += 1
			self.emit_recvMessage( recipient_sessions, msg_info )
		else:
			# On a non-default channel, and not to everyone in the room
			for session in recipient_sessions:
				self.emit_recvMessage( session, msg_info )

		self._chatserver._save_message_to_transcripts( msg_info, recipient_sessions, transcript_owners=transcript_owners )
		# Everyone who gets the transcript also
		# is considered to be on the sharing list
		msg_info.sharedWith = { recipient_session.owner for recipient_session in recipient_sessions }
		msg_info.sharedWith = msg_info.sharedWith | transcript_owners
		return True

	def add_additional_transcript_username( self, username ):
		""" Ensures that the user named `username` will get all appropriate transcripts. """
		self._addl_transcripts_to.add( username )

	def add_occupant_session_id( self, session_id, broadcast=True ):
		"""
		Adds the `session` to the group of sessions that are part of this room.
		:param bool broadcast: If `True` (the default) an event will
			be broadcast to the given session announcing it has entered the room.
			Set to False when doing bulk updates.
		"""
		sess_count_before = len( self._occupant_session_ids )
		self._occupant_session_ids.add( session_id )
		sess_count_after = len( self._occupant_session_ids )
		if broadcast and sess_count_after != sess_count_before:
			# Yay, we added one!
			self.emit_enteredRoom( session_id, self )
			self.emit_roomMembershipChanged( self.occupant_session_ids - set((session_id,)), self )
		else:
			logger.debug( "Not broadcasting (%s) enter/change events for %s in %s",
						  broadcast, session_id, self )

	def add_occupant_session_ids( self, session_ids ):
		"""
		Adds all sessions contained in the iterable `sessions` to this group
		and broadcasts an event to each new member.
		"""
		new_members = set(session_ids).difference( self.occupant_session_ids )
		old_members = self.occupant_session_ids - new_members
		self._occupant_session_ids.update( new_members )
		self.emit_enteredRoom( new_members, self )
		self.emit_roomMembershipChanged( old_members, self )

	def del_occupant_session_id( self, session_id ):
		if session_id in self._occupant_session_ids:
			_discard( self._occupant_session_ids, session_id )
			self.emit_exitedRoom( session_id, self )
			self.emit_roomMembershipChanged( self._occupant_session_ids, self )
			return True

	def toExternalDictionary( self, mergeFrom=None ):
		result = dict(mergeFrom) if mergeFrom else dict()
		result['Class'] = 'RoomInfo' # TODO: Use __external_class_name__ ?
		# TODO: Need to make this have a mime type.
		result['Moderated'] = self.Moderated
		result['Moderators'] = list(self.Moderators) # sets can't go through JSON
		result['Occupants'] = [self._chatserver.get_session( session_id ).owner
							   for session_id in self._occupant_session_ids
							   if self._chatserver.get_session( session_id )]
		# TODO: Handling shadowing and so on.
		return super(_Meeting,self).toExternalDictionary( mergeFrom=result )

	def updateFromExternalObject( self, parsed, *args, **kwargs ):
		addl_ts_needs_reset = self.inReplyTo
		super(_Meeting,self).updateFromExternalObject( parsed, *args, **kwargs )
		try:
			if addl_ts_needs_reset is not None and self.inReplyTo != addl_ts_needs_reset:
				self._addl_transcripts_to.clear()
			new_targets = self.inReplyTo.getFlattenedSharingTargetNames()
			self._addl_transcripts_to.update( new_targets )
		except AttributeError: pass

	def __repr__(self):
		return "<%s %s %s(%s)>" % (self.__class__.__name__, self.ID, self._occupant_session_ids, self.toExternalDictionary()['Occupants'])

_ChatRoom = _Meeting
deprecated('_ChatRoom', 'Prefer _Meeting' )


def _bypass_for_moderator( f ):
	def bypassing( self, msg_info ):
		if self.is_moderated_by( msg_info.sender_sid ):
			super(_ModeratedMeeting,self).post_message( msg_info )
			return True
		return f( self, msg_info )
	return bypassing

def _only_for_moderator( f ):
	def enforcing( self, msg_info ):
		if not self.is_moderated_by( msg_info.sender_sid ):
			return False
		return f( self, msg_info )
	return enforcing

class _ModeratedMeeting(_Meeting):
	"""A chat room that moderates messages."""

	__metaclass__ = _ChatObjectMeta
	__emits__ = ('recvMessageForModeration', 'recvMessageForShadow')

	_moderation_queue = None
	_moderated_by_sids = None
	_shadowed_usernames = None

	def __init__( self, *args, **kwargs ):
		super( _ModeratedMeeting, self ).__init__( *args, **kwargs )


	def _becameModerated( self ):
		self._moderated_by_sids = BTrees.OOBTree.Set()
		self._shadowed_usernames = BTrees.OOBTree.Set()
		self._moderation_queue = PersistentMapping()

	def _becomeUnmoderated( self ):
		del self._moderated_by_sids
		del self._shadowed_usernames
		del self._moderation_queue

	@property
	def moderated_by_usernames( self ):
		mod_sessions = self._find_sessions( self._moderated_by_sids )
		return {session.owner for session in mod_sessions}

	Moderators = moderated_by_usernames

	def shadowUser( self, username ):
		"""
		Causes all messages on non-default channels
		from or to this sender to be posted to all
		the moderators as well.
		"""
		self._shadowed_usernames.add( username )
		return True

	def _sids_excluded_when_considering_all( self ):
		"""
		For purposes of calculating if a message is to everyone,
		we ignore the moderators. This prevents whispering to the entire
		room, minus the teachers.
		"""
		return set( self._moderated_by_sids )

	def _is_message_on_supported_channel( self, msg_info ):
		return (msg_info.channel or CHANNEL_DEFAULT) in CHANNELS

	def post_message( self, msg_info ):
		# In moderated rooms, we break each channel out
		# to a separate function for ease of permissioning.
		msg_info.containerId = self.ID
		channel = msg_info.channel or CHANNEL_DEFAULT
		handler = getattr( self, '_msg_handle_' + str(channel), None )
		handled = False
		if handler:
			# We have a handler, but it still may not pass the pre-conditions,
			# so we don't store it here.
			handled = handler( msg_info )

		if not handled:
			if handler:
				logger.debug( 'Handler (%s) rejected message (%s) sent by %s/%s (moderators: %s/%s)',
							  handler, msg_info, msg_info.Sender, msg_info.sender_sid, list(self._moderated_by_sids), self.moderated_by_usernames )
			else:
				logger.debug( 'Dropping message on unknown channel %s', msg_info )
		return handled

	def _can_sender_whisper_to( self, msg_info ):
		"""
		Can the sender whisper to the recipients?
		Use case: The TA can whisper to anyone, students
		can only whisper to the TA. We do allow
		one-on-one whispering.
		"""
		# Right now we just use one "role" for this concept,
		# that of moderator. This will probably change.
		return msg_info.Sender in self.moderated_by_usernames \
			   or all( [recip in self.moderated_by_usernames
						for recip in msg_info.recipients_without_sender] ) \
				or len(msg_info.recipients_without_sender) == 1

	def _do_shadow_message( self, msg_info ):
		if any( [recip in self._shadowed_usernames
				 for recip in msg_info.recipients_with_sender] ):
			msg_info.Status = STATUS_SHADOWED
			self._ensure_message_stored( msg_info )
			self.emit_recvMessageForShadow( self._moderated_by_sids, msg_info )
			self._chatserver._save_message_to_transcripts( msg_info, self._moderated_by_sids )

	@_bypass_for_moderator
	def _msg_handle_WHISPER( self, msg_info ):
		if self._is_message_to_all_occupants( msg_info ) \
		   and len(msg_info.recipients_without_sender) > 1:
			# Whispering to everyone is just like posting to the default
			# channel. We make a special exception when there's only
			# one other person besides the moderator in the room,
			# to enable peer-to-peer whispering
			return self._msg_handle_DEFAULT( msg_info )

		if self._can_sender_whisper_to( msg_info ):
			self._do_shadow_message( msg_info )
			super( _ModeratedMeeting, self ).post_message( msg_info )
			return True

	@_bypass_for_moderator
	def _msg_handle_DEFAULT( self, msg_info ):
		self._ensure_message_stored( msg_info )
		self._moderation_queue[msg_info.MessageId] = msg_info
		msg_info.Status = STATUS_PENDING
		self.emit_recvMessageForModeration( self._moderated_by_sids, msg_info )
		return True

	@_only_for_moderator
	def _msg_handle_CONTENT( self, msg_info ):
		if not isinstance( msg_info.body, collections.Mapping ) \
		   or not 'ntiid' in msg_info.body \
		   or not ntiids.is_valid_ntiid_string( msg_info.body['ntiid'] ):
			return False
		# sanitize any keys we don't know about.
		msg_info.body = {'ntiid': msg_info.body['ntiid'] }
		# Recipients are ignored, message goes to everyone
		msg_info.recipients = []
		# And now broadcast
		super(_ModeratedMeeting,self).post_message( msg_info )
		return True

	@_only_for_moderator
	def _msg_handle_META( self, msg_info ):
		# Right now, we support two actions. As this grows,
		# we'll need to refactor appropriately, like with channels.
		ACTIONS = ('pin', 'clearPinned')
		if not isinstance( msg_info.body, collections.Mapping ) \
		   or 'channel' not in msg_info.body or msg_info.body['channel'] not in CHANNELS \
		   or 'action' not in msg_info.body or msg_info.body['action'] not in ACTIONS:
			return False

		# In all cases, these are broadcasts
		msg_info.recipients = ()
		if msg_info.body['action'] == 'pin':
			if not ntiids.is_valid_ntiid_string( msg_info.body.get( 'ntiid', None ) ):
				return False
			#sanitize the body
			msg_info.body = { k: msg_info.body[k] for k in ('channel', 'action', 'ntiid') }
			super(_ModeratedMeeting,self).post_message( msg_info )
		elif msg_info.body['action'] == 'clearPinned':
			# sanitize the body
			msg_info.body = { k: msg_info.body[k] for k in ('channel', 'action') }
			super(_ModeratedMeeting,self).post_message( msg_info )
		else:
			raise NotImplementedError( 'Meta action ' + str(msg_info.body['action']) )

		return True

	def _msg_handle_POLL( self, msg_info ):
		if self.is_moderated_by( msg_info.sender_sid ):
			# TODO: Track the OIDs of these messages so we can
			# validate replies
			# TODO: Validate body, when we decide what that is
			# This is a broadcast (TODO: Always?)
			msg_info.recipients = ()
			super(_ModeratedMeeting,self).post_message( msg_info )
			return True

		if not msg_info.inReplyTo:
			# TODO: Track replies.
			return False

		# replies (answers) go only to the moderators
		msg_info.recipients = self.moderated_by_usernames
		super(_ModeratedMeeting,self).post_message( msg_info )
		return True


	def add_moderator( self, mod_sid ):
		self._moderated_by_sids.add( mod_sid )

	def is_moderated_by( self, mod_sid ):
		return mod_sid in self._moderated_by_sids

	def approve_message( self, msg_id ):
		# TODO: Disapprove messages? This queue could get terrifically
		# large.
		msg = self._moderation_queue.pop( msg_id, None )
		if msg:
			msg.Status = STATUS_POSTED
			super(_ModeratedMeeting, self).post_message( msg )

_ModeratedChatRoom = _ModeratedMeeting
deprecated('_ModeratedChatRoom', 'Prefer _ModeratedMeeting' )

def ChatHandlerFactory( socketio_protocol, chatserver=None ):
	session = socketio_protocol.session if hasattr( socketio_protocol, 'session' ) else socketio_protocol
	if session:
		chatserver = component.getUtility( nti_interfaces.IChatserver ) if not chatserver else chatserver
		return _ChatHandler( chatserver, session )
	logger.warning( "No session (%s); could not create event handler.", session )

class PersistentMappingMeetingStorage(Persistent):
	"""
	An implementation of :class:`chat_interfaces.IMeetingStorage` using
	some sort of persistent mapping. The default is in fact
	:class:`PersistentMapping`, but this may be changed at construction.
	"""
	interface.implements(chat_interfaces.IMeetingStorage)

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

		room.id = datastructures.to_external_ntiid_oid( room, None )
		if room.id is None:
			raise ValueError( "Unable to assign ID, not persistent" )
		self.meetings[room.id] = room

	def get( self, room_id ):
		return self.meetings.get( room_id )



class Chatserver(object):
	""" Collection of all the state related to the chatserver, including active rooms, etc. """

	_chatserver = None

	### Pickling
	# This is an attempt to return a singleton
	# chatserver when pickled. It doesn't
	# seem to quite work (I wind up with
	# and empty instance dict), hence
	# shadowing the variables in __init__.

	def __new__( cls, *args, **kwargs ):
		if len(args) == 2 and args[1] == 42:
			return Chatserver._chatserver
		return super(Chatserver,cls).__new__( cls, *args, **kwargs )

	def __getnewargs__( self ):
		return (42,)

	def __getstate__( self ):
		return {}

	interface.implements( nti_interfaces.IChatserver )

	def __init__( self, user_sessions, meeting_storage=None,
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

		# FIXME: The pickling problem mentioned above.
		Chatserver.rooms = self.rooms
		Chatserver.sessions = self.sessions
		Chatserver.meeting_container_storage = self.meeting_container_storage
		Chatserver._chatserver = self

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

	def get_session( self, session_id ):
		return session_id if hasattr( session_id, 'protocol_handler' ) else self.sessions.get_session( session_id )

	### Low-level IO

	def send_event( self, session_id, name, *args ):
		session = self.get_session( session_id )
		if session:
			args = [datastructures.toExternalObject( arg ) for arg in args]
			session.protocol_handler.send_event( name, *args )

	### General events
	# We are directing these events to all sessions connected for the user
	def _notify_target( self, target, meth_name, *args ):
		candidates = list( self.sessions.get_sessions_by_owner( target ) )
		candidates.sort( key=lambda x: x.creation_time, reverse=True )
		for sess in candidates:
			try:
				getattr( ChatHandlerFactory( sess, chatserver=self ),
						 meth_name )( sess, *args )
			except Exception:
				logger.exception( "Failed to %s to %s", meth_name, sess )

	def notify_presence_change( self, sender, new_presence, targets ):
		for target in set(targets):
			self._notify_target( target, 'emit_presenceOfUserChangedTo', sender, new_presence )

	@deprecate("We need to replace this with something not directly tied to IChatserver/chat.py")
	def notify_data_change( self, target, change ):
		self._notify_target( target, 'emit_data_noticeIncomingChange', change )

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
			logger.info( "The container %s (%s) is not a persistent meeting room", container, room_info_dict )
			return None

		# At this point, we know we have exactly one Occupant, the (sender,sid).
		# This next call MIGHT change that, so preserve it.
		occupant_tuple = room_info_dict['Occupants'][0]
		room = container.enter_active_meeting( self, room_info_dict )
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
		if room and len(room.occupant_sessions) == 0 and len(room.occupant_session_ids) > 0:
			logger.debug( "Clearing out all stale sessions from %s", room )
			for sid in room.occupant_session_ids:
				self.exit_meeting( room.RoomId, sid )
			room = None
		if room:
			logger.debug( "%s entering existing persistent meeting %s", occupant_tuple, room )
			# Yes, we got in. Announce this.
			room.add_occupant_session_id( occupant_tuple[1] )
		else:
			# We didn't get in. We know we have a container, though,
			# so see if we can start one.
			logger.debug( "%s creating new persistent meeting %s", occupant_tuple, room_info_dict )
			room = self.create_room_from_dict( room_info_dict )
		return room

	def create_room_from_dict( self, room_info_dict ):
		"""
		:param dict room_info_dict: Contains at least an `Occupants` key. This key
			is an iterable of usernames or (username,session_id) tuples.

		Creates a room given a dictionary of values.
		"""

		room_info_dict = dict( room_info_dict ) # copy because we will modify

		# We need to resolve names into sessions, whether or not there
		# is a container, so we do it now.

		room = None
		# If the container is specified, and is found as something
		# that wants to have a say, let it.
		if XFields.CONTAINER_ID in room_info_dict:
			container = self.meeting_container_storage.get( room_info_dict[XFields.CONTAINER_ID] )
			if hasattr( container, 'create_meeting_from_dict' ):
				# The container will decide what to do with things like
				# Occupants, they may ignore it or replace it entirely.
				room = container.create_meeting_from_dict( self, room_info_dict, lambda: _Meeting(self) )
				if room is None or not room.Active:
					logger.debug( "Container %s vetoed creation of room %s (%s)",
								  container, room, room_info_dict )
					# The container vetoed creation for some reason.
					return None
				# Containers deal with, roughly, persistent rooms. Therefore, if they
				# give us a list of occupants, then regardless of whether
				# they are currently online these occupants should get transcripts.
				for occupant in room_info_dict['Occupants']:
					if isinstance( occupant, tuple ): occupant = occupant[0]
					room.add_additional_transcript_username( occupant )

		if room is None:
			room = _Meeting(self)

		# Resolve occupants
		sessions = []
		for occupant in room_info_dict['Occupants']:
			session = None
			session_ids = None
			if isinstance( occupant, tuple ):
				# Two-tuples give us the session ID
				session_ids = occupant[1]
				occupant = occupant[0]
			session = self.get_session_for( occupant, session_ids )
			if session:	sessions.append( session.session_id )
		if not sessions:
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
		self.rooms.add_room( room )

		room.add_occupant_session_ids( sessions )
		return room

	def get_meeting( self, room_id ):
		return self.rooms.get( room_id )

	def exit_meeting( self, room_id, session_id ):
		"""
		:return: Value indicating successful exit.
		"""
		result = None
		room = self.rooms.get( room_id )
		if room:
			result = room.del_occupant_session_id( session_id )
			if not room.occupant_session_ids:
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

	def _ts_storage_for( self, session, create_if_missing=True ):
		owner = session.owner if hasattr(session,'owner') else session
		storage = None
		if owner:
			# TODO: Need a component to resolve users
			user = users.User.get_user( owner )
			storage = component.queryAdapter( user, chat_interfaces.IUserTranscriptStorage ) \
					if user \
					else None
		return storage

	def _save_message_to_transcripts( self, msg_info, transcript_sids, transcript_owners=() ):
		"""
		Adds the message to the transcripts of each user given.

		:param MessageInfo msg_info: The message. Must have a container id.
		:param iterable transcript_sids: Iterable of session ids or sessions to post the message to.
		:param iterable transcript_owners: Iterable of usernames to post the message to.
		"""
		owners = set( transcript_owners )

		for sid in transcript_sids:
			sess = self.get_session( sid )
			if not sess: continue
			owners.add( sess.owner )

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
		result = datastructures.CreatedModDateTrackingPersistentMapping( data )
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

import ZODB.interfaces
from BTrees import OOBTree
