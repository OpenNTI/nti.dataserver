""" Chatserver functionality. """

__docformat__ = "restructuredtext en"

import logging
logger = logging.getLogger( __name__ )

import time
import collections
import functools


from nti.ntiids import ntiids
from nti.externalization import datastructures
from nti.zodb.minmax import MergingCounter

# TODO: Break this dep
from nti.dataserver import contenttypes

import persistent
from persistent import Persistent
import BTrees.OOBTree

from zope import interface
from zope import component
from zope.deprecation import deprecated
from zope.event import notify


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

# bwc with objects stored in the database.
# TODO: There's a zope utility to take care of movements like this
from ._meeting_post_policy import _ModeratedMeetingState




class _Meeting(contenttypes.ThreadableExternalizableMixin,
				Persistent,
				datastructures.ExternalizableInstanceDict):
	"""Class to handle distributing messages to clients. """

	__metaclass__ = _ChatObjectMeta
	__emits__ = ('recvMessage', 'enteredRoom', 'exitedRoom',
				 'roomMembershipChanged', 'roomModerationChanged' )

	interface.implements(interfaces.IMeeting)

	_prefer_oid_ = False

	Active = True
	creator = None

	_v_chatserver = None
	_moderation_state = None
	_occupant_names = ()
	def __init__( self, chatserver=None ):
		super(_Meeting,self).__init__()
		self._v_chatserver = chatserver
		self.id = None
		self.containerId = None
		self._MessageCount = MergingCounter( 0 )
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

	@property
	def MessageCount(self):
		# Can only set this directly, setting as a property
		# leads to false conflicts
		return self._MessageCount.value

	def __setstate__( self, state ):
		# Migration 2012-04-03. Easier than searching these all out (because many are
		# not reachable from the root, due to cross-db refs)
		if 'MessageCount' in state:
			state = dict(state)
			state['_MessageCount'] = MergingCounter( state['MessageCount'] )
			del state['MessageCount']
		if '_chatserver' in state:
			state = dict(state)
			del state['_chatserver']

		# Migration 2012-04-19
		if '_occupant_session_ids' in state:
			state = dict(state)
			del state['_occupant_session_ids']

		# Missed part of that migration
		if '_occupant_names' not in state:
			state = dict(state)
			state['_occupant_names'] = BTrees.OOBTree.Set()

		if '_moderated' in state:
			state = dict(state)
			del state['_moderated']

		super(_Meeting,self).__setstate__( state )

	@property
	def RoomId(self):
		return self.id
	@property
	def ID(self):
		return self.id

	def _Moderated( self ):
		return self._moderation_state is not None

	def _setModerated( self, flag ):
		if flag and self._moderation_state is None:
			notify( interfaces.MeetingShouldChangeModerationStateEvent( self, flag ) )
			self.emit_roomModerationChanged( self._occupant_names, self )
		elif not flag and self._moderation_state is not None:
			notify( interfaces.MeetingShouldChangeModerationStateEvent( self, flag ) )
			self.emit_roomModerationChanged( self._occupant_names, self )

	Moderated = property( _Moderated, _setModerated )

	@property
	def Moderators(self):
		return self._policy().moderated_by_usernames

	@property
	def occupant_session_names(self):
		"""
		:return: An iterable of the names of all active users in this room.
			See :meth:`occupant_sessions`.
		"""
		return frozenset(self._occupant_names)
	occupant_names = occupant_session_names

	def _policy(self):
		return interfaces.IMeetingPolicy( self )

	def post_message( self, msg_info ):
		result = self._policy().post_message( msg_info )
		if result == 1:
			self._MessageCount.increment()
		return result

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

	def add_occupant_names( self, names, broadcast=True ):
		"""
		Adds all sessions contained in the iterable `names` to this group
		and broadcasts an event to each new member.
		:param bool broadcast: If ``True`` (the default) an event will
			be broadcast to all new members and to all old members.
		"""
		new_members = set(names).difference( self.occupant_names )
		old_members = self.occupant_names - new_members
		self._occupant_names.update( new_members )
		if broadcast:
			self.emit_enteredRoom( new_members, self )
			self.emit_roomMembershipChanged( old_members, self )

	def del_occupant_name( self, name ):
		if name in self._occupant_names:
			_discard( self._occupant_names, name )
			self.emit_exitedRoom( name, self )
			self.emit_roomMembershipChanged( self._occupant_names, self )
			return True

	def add_moderator( self, mod_name ):
		self._policy().add_moderator( mod_name )

	def is_moderated_by( self, mod_name ):
		return self._moderated.is_moderated_by( mod_name )

	def approve_message( self, msg_id ):
		return self._policy().approve_message( msg_id )

	def shadow_user( self, username ):
		return self._policy().shadow_user( username )

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
_ModeratedMeeting = _Meeting
deprecated('_ModeratedMeeting', 'No distinction anymore' )

_ModeratedChatRoom = _ModeratedMeeting
deprecated('_ModeratedChatRoom', 'Prefer _ModeratedMeeting' )
