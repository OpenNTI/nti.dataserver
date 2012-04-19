""" Chatserver functionality. """

__docformat__ = "restructuredtext en"

import logging
logger = logging.getLogger( __name__ )

import time
import collections


from nti.dataserver import ntiids
from nti.dataserver import datastructures
from nti.dataserver import contenttypes

import persistent
from persistent import Persistent
from persistent.mapping import PersistentMapping
import BTrees.OOBTree

from zope import interface
from zope import component
from zope.deprecation import deprecated

from zope import minmax

from . import interfaces
from ._metaclass import _ChatObjectMeta
from .interfaces import CHANNEL_DEFAULT, CHANNEL_WHISPER, CHANNELS
from .interfaces import STATUS_POSTED, STATUS_SHADOWED, STATUS_PENDING #, STATUS_INITIAL

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
EVT_EXITED_ROOM  = 'chat_exitedRoom'
EVT_POST_MESSOGE = 'chat_postMessage'
EVT_RECV_MESSAGE = 'chat_recvMessage'


def _discard( s, k ):
	try:
		s.discard( k ) # python sets
	except AttributeError:
		try:
			s.remove( k ) # OOSet, list
		except (KeyError,ValueError): pass



class _Meeting(contenttypes.ThreadableExternalizableMixin,
				Persistent,
				datastructures.ExternalizableInstanceDict):
	"""Class to handle distributing messages to clients. """

	__metaclass__ = _ChatObjectMeta
	__emits__ = ('recvMessage', 'enteredRoom', 'exitedRoom',
				 'roomMembershipChanged', 'roomModerationChanged' )
	_prefer_oid_ = False


	_v_chatserver = None
	Active = True
	_moderated = False
	_occupant_names = ()
	def __init__( self, chatserver ):
		super(_Meeting,self).__init__()
		self._v_chatserver = chatserver
		self.id = None
		self.containerId = None
		self._MessageCount = datastructures.MergingCounter( 0 )
		self.CreatedTime = time.time()
		self._occupant_names = BTrees.OOBTree.Set()
		# Sometimes a room is created with a subset of the occupants that
		# should receive transcripts. The most notable case of this is
		# creating a room in reply to something that's shared: everyone
		# that it is shared with should get the transcript even if they
		# didn't participate in the room because they were offline.
		# TODO: How does this interact with things that are
		# shared publically and not specific users?
		self._addl_transcripts_to = BTrees.OOBTree.Set()


	def _get_chatserver(self):
		return self._v_chatserver or component.queryUtility( interfaces.IChatserver )
	def _set_chatserver( self, cs ):
		self._v_chatserver = cs
	_chatserver = property(_get_chatserver, _set_chatserver )

	def _get_MessageCount(self):
		return self._MessageCount.value
	def _set_MessageCount(self,nv):
		self._MessageCount.value = nv
	MessageCount = property(_get_MessageCount,_set_MessageCount)

	def __setstate__( self, state ):
		# Migration 2012-04-03. Easier than searching these all out
		if 'MessageCount' in state:
			state = dict(state)
			state['_MessageCount'] = datastructures.MergingCounter( state['MessageCount'] )
			del state['MessageCount']
		if '_chatserver' in state:
			state = dict(state)
			del state['_chatserver']

		# Migration 2012-04-19
		if '_occupant_session_ids' in state:
			state = dict(state)
			del state['_occupant_session_ids']


		super(_Meeting,self).__setstate__( state )
		# Because we are swizzling classes dynamically at
		# runtime, that fact may not be persisted in the database.
		# We have to restore it when the object comes alive.
		# This is tightly coupled with the implementation of
		# _becameModerated/_becameUnmoderated
		if state.get( '_moderated' ) and self.__class__ == _Meeting:
			self.__class__ = _ModeratedMeeting

			if not '_moderated_by_names' in state:
				# Belt and suspenders
				logger.warn( "Inconsistent state of meeting %s", state )
				self._moderated = False
				self.__class__ = _Meeting

	def _p_resolveConflict( self, old, saved, new ):
		# FIXME: It's not clear what could be actually conflicting
		logger.warn( "Resolving conflict in Meeting. \n%s\n%s\n%s", old, saved, new )
		return new

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
				# become unmoderated.
				self._becomeUnmoderated()
				self.__class__ = _Meeting
			self.emit_roomModerationChanged( self._occupant_names, self )

	Moderated = property( _Moderated, _setModerated )
	Moderators = ()

	@property
	def occupant_session_names(self):
		"""
		:return: An iterable of the names of all active users in this room.
			See :meth:`occupant_sessions`.
		"""
		return frozenset(self._occupant_names)
	occupant_names = occupant_session_names

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

	def _get_recipient_names_for_message( self, msg_info ):
		if self._treat_recipients_like_default_channel( msg_info ):
			recipient_names = set(self._occupant_names )
		else:
			requested = set(msg_info.recipients_with_sender)
			recipient_names = set( self._occupant_names ).intersection( requested )
		recipient_names.discard( None )
		return recipient_names

	def _names_excluded_when_considering_all( self ):
		"""
		:return: A set of sids excluded when comparing against all occupants.
		"""
		return set()

	def _is_message_to_all_occupants( self, msg_info, recipient_names=None ):
		"""
		Should the message be treated as if it were the default
		channel? Yes, if it is either to the DEFAULT channel, an empty recipient list, or its recipient list
		is to everyone (not excluded by :meth:`_names_excluded_when_considering_all`)
		"""
		if self._treat_recipients_like_default_channel( msg_info ):
			return True
		return (recipient_names or self._get_recipient_names_for_message( msg_info )) \
			   == (set(self._occupant_names) - self._names_excluded_when_considering_all())

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
		recipient_names = self._get_recipient_names_for_message( msg_info )

		if self._is_message_to_all_occupants( msg_info, recipient_names=recipient_names ):
			# recipients are ignored for the default channel,
			# and a message to everyone also counts for incrementing the ids.
			self.MessageCount += 1
			self.emit_recvMessage( recipient_names, msg_info )
		else:
			# On a non-default channel, and not to everyone in the room
			for name in recipient_names:
				self.emit_recvMessage( name, msg_info )

		self._chatserver._save_message_to_transcripts( msg_info, recipient_names, transcript_owners=transcript_owners )
		# Everyone who gets the transcript also
		# is considered to be on the sharing list
		msg_info.sharedWith = set(recipient_names)
		msg_info.sharedWith = msg_info.sharedWith | transcript_owners
		return True

	def add_additional_transcript_username( self, username ):
		""" Ensures that the user named `username` will get all appropriate transcripts. """
		self._addl_transcripts_to.add( username )

	def add_occupant_name( self, name, broadcast=True ):
		"""
		Adds the `session` to the group of sessions that are part of this room.
		:param bool broadcast: If `True` (the default) an event will
			be broadcast to the given session announcing it has entered the room.
			Set to False when doing bulk updates.
		"""
		sess_count_before = len( self._occupant_names )
		self._occupant_names.add( name )
		sess_count_after = len( self._occupant_names )
		if broadcast and sess_count_after != sess_count_before:
			# Yay, we added one!
			self.emit_enteredRoom( name, self )
			self.emit_roomMembershipChanged( self.occupant_names - set((name,)), self )
		else:
			logger.debug( "Not broadcasting (%s) enter/change events for %s in %s",
						  broadcast, name, self )

	def add_occupant_names( self, names ):
		"""
		Adds all sessions contained in the iterable `names` to this group
		and broadcasts an event to each new member.
		"""
		new_members = set(names).difference( self.occupant_names )
		old_members = self.occupant_names - new_members
		self._occupant_names.update( new_members )
		self.emit_enteredRoom( new_members, self )
		self.emit_roomMembershipChanged( old_members, self )

	def del_occupant_name( self, name ):
		if name in self._occupant_names:
			_discard( self._occupant_names, name )
			self.emit_exitedRoom( name, self )
			self.emit_roomMembershipChanged( self._occupant_names, self )
			return True

	def toExternalDictionary( self, mergeFrom=None ):
		result = dict(mergeFrom) if mergeFrom else dict()
		result['Class'] = 'RoomInfo' # TODO: Use __external_class_name__ ?
		# TODO: Need to make this have a mime type.
		result['Moderated'] = self.Moderated
		result['Moderators'] = list(self.Moderators) # sets can't go through JSON
		result['Occupants'] = list(self.occupant_names)
		result['MessageCount'] = self.MessageCount
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
		return "<%s %s %s>" % (self.__class__.__name__, self.ID, self._occupant_names)

_ChatRoom = _Meeting
deprecated('_ChatRoom', 'Prefer _Meeting' )


def _bypass_for_moderator( f ):
	def bypassing( self, msg_info ):
		if self.is_moderated_by( msg_info.Sender ):
			super(_ModeratedMeeting,self).post_message( msg_info )
			return True
		return f( self, msg_info )
	return bypassing

def _only_for_moderator( f ):
	def enforcing( self, msg_info ):
		if not self.is_moderated_by( msg_info.Sender ):
			return False
		return f( self, msg_info )
	return enforcing

class _ModeratedMeeting(_Meeting):
	"""A chat room that moderates messages."""

	__metaclass__ = _ChatObjectMeta
	__emits__ = ('recvMessageForModeration', 'recvMessageForShadow')

	_moderation_queue = ()
	_moderated_by_names = ()
	_shadowed_usernames = ()

	def __init__( self, *args, **kwargs ):
		super( _ModeratedMeeting, self ).__init__( *args, **kwargs )


	def _becameModerated( self ):
		self._moderated_by_names = BTrees.OOBTree.Set()
		self._shadowed_usernames = BTrees.OOBTree.Set()
		self._moderation_queue = PersistentMapping()

	def _becomeUnmoderated( self ):
		del self._moderated_by_names
		del self._shadowed_usernames
		del self._moderation_queue

	@property
	def moderated_by_usernames( self ):
		return frozenset( self._moderated_by_names )

	Moderators = moderated_by_usernames

	def shadowUser( self, username ):
		"""
		Causes all messages on non-default channels
		from or to this sender to be posted to all
		the moderators as well.
		"""
		self._shadowed_usernames.add( username )
		return True

	def _names_excluded_when_considering_all( self ):
		"""
		For purposes of calculating if a message is to everyone,
		we ignore the moderators. This prevents whispering to the entire
		room, minus the teachers.
		"""
		return set( self._moderated_by_names )

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
							  handler, msg_info, msg_info.Sender, msg_info.Sender, list(self._moderated_by_names), self.moderated_by_usernames )
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
			self.emit_recvMessageForShadow( self._moderated_by_names, msg_info )
			self._chatserver._save_message_to_transcripts( msg_info, self._moderated_by_names )

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
		self.emit_recvMessageForModeration( self._moderated_by_names, msg_info )
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
		if self.is_moderated_by( msg_info.Sender ):
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


	def add_moderator( self, mod_name ):
		self._moderated_by_names.add( mod_name )
		self.emit_roomModerationChanged( self._occupant_names, self )

	def is_moderated_by( self, mod_name ):
		return mod_name in self._moderated_by_names

	def approve_message( self, msg_id ):
		# TODO: Disapprove messages? This queue could get terrifically
		# large.
		msg = self._moderation_queue.pop( msg_id, None )
		if msg:
			msg.Status = STATUS_POSTED
			super(_ModeratedMeeting, self).post_message( msg )

_ModeratedChatRoom = _ModeratedMeeting
deprecated('_ModeratedChatRoom', 'Prefer _ModeratedMeeting' )
