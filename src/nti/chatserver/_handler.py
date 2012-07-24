#!/usr/bin/env python
""" Chatserver functionality. """
from __future__ import print_function, unicode_literals

__docformat__ = "restructuredtext en"

import logging
logger = logging.getLogger( __name__ )

import warnings


from nti.externalization.interfaces import StandardExternalFields as XFields
from nti.socketio import interfaces as sio_interfaces

# FIXME: Break this dependency
from nti.dataserver import users
from nti.dataserver import authorization_acl as auth_acl


from persistent import Persistent
from persistent.mapping import PersistentMapping

from zope import interface
from zope import component


from ._metaclass import _ChatObjectMeta
from . import interfaces


EVT_ENTERED_ROOM = 'chat_enteredRoom'
EVT_EXITED_ROOM = 'chat_exitedRoom'
EVT_POST_MESSOGE = 'chat_postMessage'
EVT_RECV_MESSAGE = 'chat_recvMessage'



from nti.utils.sets import discard as _discard

class IChatHandlerSessionState(interface.Interface):
	rooms_i_moderate = interface.Attribute( "Mapping of rooms I moderate" )

@interface.implementer(IChatHandlerSessionState)
@component.adapter(sio_interfaces.ISocketSession)
class _ChatHandlerSessionState(Persistent):
	"""
	An annotation for sessions to store the state a chat handler likes to have,
	since chat handlers have no state for longer than a single event.
	"""

	def __init__(self):
		self.rooms_i_moderate = PersistentMapping()

from zope.annotation import factory as an_factory
def _ChatHandlerSessionStateFactory(session):
	return an_factory(_ChatHandlerSessionState)(session)

@interface.implementer(sio_interfaces.ISocketEventHandler)
class _ChatHandler(object):
	"""
	Class to handle each of the messages sent to or from a client.

	Instances of this class are tied to the session, not the chatserver.
	They should go away when the user's session does.
	"""

	__metaclass__ = _ChatObjectMeta
	__emits__ = ('recvMessageForAttention', 'presenceOfUserChangedTo',
				 'data_noticeIncomingChange', 'failedToEnterRoom' )
	_session_consumer_args_search_ = ('nti.chatserver.meeting','nti.chatserver.messageinfo')


	event_prefix = 'chat'
	_v_chatserver = None
	# public methods correspond to events

	def __init__( self, chatserver, session ):
		""" """
		self._v_chatserver = chatserver
		self.session = session

	def __reduce__(self):
		raise TypeError()

	def __str__( self ):
		return "%s(%s %s)" % (self.__class__.__name__, self.session.owner, self.session.session_id)

	# None of these should be around anymore
	# def __setstate__( self, state ):
	# 	# Migration 2012-04-18. Easier than searching these all out
	# 	if '_chatserver' in state:
	# 		state = dict(state)
	# 		del state['_chatserver']

	# 	super(_ChatHandler,self).__setstate__( state )

	def _get_chatserver(self):
		return self._v_chatserver or component.queryUtility( interfaces.IChatserver )
	def _set_chatserver( self, cs ):
		self._v_chatserver = cs
	_chatserver = property(_get_chatserver, _set_chatserver )

	def postMessage( self, msg_info ):
		# Ensure that the sender correctly matches.
		msg_info.Sender = self.session.owner
		msg_info.sender_sid = self.session.session_id
		result = True
		for room in set(msg_info.rooms):
			result &= self._chatserver.post_message_to_room( room, msg_info )
		return result

	def enterRoom( self, room_info ):
		room = None
		room_info['Creator'] = self.session.owner
		if room_info.get( 'RoomId' ) is not None:
			# Trying to join an established room
			# Right now, unsupported.
			logger.debug( "Cannot enter existing room %s", room_info )
		elif len( room_info.get( 'Occupants', () ) ) == 0 and XFields.CONTAINER_ID in room_info:
			# No occupants, but a container ID. This must be for something
			# that can persistently host meetings. We want
			# to either create or join it.
			room_info['Occupants'] = [ (self.session.owner, self.session.session_id ) ]
			room = self._chatserver.enter_meeting_in_container( room_info )
		else:
			# Creating a room to chat with. Make sure I'm in it.
			# More than that, make sure it's my session, and any
			# of my friends lists are expanded. Make sure it has an active
			# occupant besides me
			_discard( room_info.get('Occupants'), self.session.owner )
			room_info['Occupants'] = list( room_info['Occupants'] )
			user = users.User.get_user( self.session.owner )
			if user:
				for i in list(room_info['Occupants']):
					if i in user.friendsLists:
						room_info['Occupants'] += [x.username for x in user.friendsLists[i]]
			room_info['Occupants'].append( (self.session.owner, self.session.session_id) )
			def sessions_validator(sessions):
				"""
				We can only create the ad-hoc room if there is another online occupant.
				"""
				return len(sessions) > 1
			room = self._chatserver.create_room_from_dict( room_info, sessions_validator=sessions_validator )

		if not room:
			self.emit_failedToEnterRoom( self.session.owner, room_info )
		return room

	def exitRoom( self, room_id ):
		result = self._chatserver.exit_meeting( room_id, self.session.owner )
		return result

	def makeModerated( self, room_id, flag ):

		room = self._chatserver.get_meeting( room_id )
		can_moderate = auth_acl.has_permission( interfaces.ACT_MODERATE, room, self.session.owner )
		if not can_moderate:
			logger.debug( "%s not allowed to moderate room %s: %s", self, room, can_moderate )
			return room

		if flag:
			if flag != room.Moderated:
				room.Moderated = flag
			logger.debug( "%s becoming a moderator of room %s", self, room )
			room.add_moderator( self.session.owner )
			IChatHandlerSessionState(self.session).rooms_i_moderate[room.RoomId] = room
		else:
			# deactivating moderation for the room
			# TODO: We need to 'pop' rooms_i_moderate in all the other handlers.
			# Thats only a minor problem, though
			if flag != room.Moderated:
				logger.debug( "%s deactivating moderation of %s", self, room )
				room.Moderated = flag
			IChatHandlerSessionState(self.session).rooms_i_moderate.pop( room.RoomId, None )
		return room

	def approveMessages( self, m_ids ):
		for m in m_ids:
			for room in IChatHandlerSessionState(self.session).rooms_i_moderate.itervalues():
				room.approve_message( m )

	def flagMessagesToUsers( self, m_ids, usernames ):
		# TODO: Roles again. Who can flag to whom?
		warnings.warn( "Allowing anyone to flag messages to users." )
		warnings.warn( "Assuming that clients have seen messages flagged to them." )
		for m in m_ids:
			# TODO: Where does this state belong? Who
			# keeps the message? Passing just the ID assumes
			# that the client can find the message by id.
			self.emit_recvMessageForAttention( usernames, m )
		return True

	def shadowUsers( self, room_id, usernames ):
		room = self._chatserver.get_meeting( room_id )
		can_moderate = auth_acl.has_permission( interfaces.ACT_MODERATE, room, self.session.owner )
		if not can_moderate:
			logger.debug( "%s not allowed to shadow in room %s: %s", self, room, can_moderate )
			return False

		result = False
		if room and room.Moderated:
			result = True
			for user in usernames:
				result &= room.shadow_user( user )
		return result


def ChatHandlerFactory( socketio_protocol, chatserver=None ):
	session = socketio_protocol.session if hasattr( socketio_protocol, 'session' ) else socketio_protocol
	if session:
		chatserver = component.queryUtility( interfaces.IChatserver ) if not chatserver else chatserver
	if session and chatserver:
		return _ChatHandler( chatserver, session )
	logger.warning( "No session (%s) or chatserver (%s); could not create event handler.", session, chatserver )
