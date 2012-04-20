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


from persistent import Persistent
from persistent.mapping import PersistentMapping
import BTrees.OOBTree

from zope import interface
from zope import component
from zope.deprecation import deprecate, deprecated
from zope import minmax

from ._metaclass import _ChatObjectMeta
from . import interfaces

class _AlwaysIn(object):
	"""Everything is `in` this class."""
	def __init__(self): pass
	def __contains__(self,obj): return True




EVT_ENTERED_ROOM = 'chat_enteredRoom'
EVT_EXITED_ROOM = 'chat_exitedRoom'
EVT_POST_MESSOGE = 'chat_postMessage'
EVT_RECV_MESSAGE = 'chat_recvMessage'




def _discard( s, k ):
	try:
		s.discard( k ) # python sets
	except AttributeError:
		try:
			s.remove( k ) # OOSet, list
		except (KeyError,ValueError): pass


class _ChatHandler( Persistent ):
	"""
	Class to handle each of the messages sent to or from a client.

	Instances of this class are tied to the session, not the chatserver.
	They should go away when the user's session does.
	"""

	__metaclass__ = _ChatObjectMeta
	__emits__ = ('recvMessageForAttention', 'presenceOfUserChangedTo',
				 'data_noticeIncomingChange', 'failedToEnterRoom' )
	_session_consumer_args_search_ = ('nti.chatserver.meeting','nti.chatserver.messageinfo')

	interface.implements(sio_interfaces.ISocketEventHandler)
	event_prefix = 'chat'
	_v_chatserver = None
	# public methods correspond to events

	def __init__( self, chatserver, session ):
		""" """
		self._v_chatserver = chatserver
		self.session_id = session.session_id
		self.session_owner = session.owner
		self.rooms_i_moderate = PersistentMapping()
		self.rooms_im_in = BTrees.OOBTree.Set()

	def __str__( self ):
		return "%s(%s %s)" % (self.__class__.__name__, self.session_owner, self.session_id)


	def __setstate__( self, state ):
		# Migration 2012-04-18. Easier than searching these all out
		if '_chatserver' in state:
			state = dict(state)
			del state['_chatserver']

		super(_ChatHandler,self).__setstate__( state )

	def _get_chatserver(self):
		return self._v_chatserver or component.queryUtility( interfaces.IChatserver )
	def _set_chatserver( self, cs ):
		self._v_chatserver = cs
	_chatserver = property(_get_chatserver, _set_chatserver )

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
			# of my friends lists are expanded. Make sure it has an active
			# occupant besides me
			_discard( room_info.get('Occupants'), self.session_owner )
			room_info['Occupants'] = list( room_info['Occupants'] )
			user = users.User.get_user( self.session_owner )
			if user:
				for i in list(room_info['Occupants']):
					if i in user.friendsLists:
						room_info['Occupants'] += [x.username for x in user.friendsLists[i]]
			room_info['Occupants'].append( (self.session_owner, self.session_id) )
			def sessions_validator(sessions):
				"""
				We can only create the ad-hoc room if there is another online occupant.
				"""
				return len(sessions) > 1
			room = self._chatserver.create_room_from_dict( room_info, sessions_validator=sessions_validator )

		if room:
			self.rooms_im_in.add( room.RoomId )
		else:
			self.emit_failedToEnterRoom( self.session_owner, room_info )
		return room

	def exitRoom( self, room_id ):
		result = self._chatserver.exit_meeting( room_id, self.session_owner )
		_discard( self.rooms_im_in, room_id )
		return result

	def makeModerated( self, room_id, flag ):
		# TODO: Roles. Who can moderate?
		room = self._chatserver.get_meeting( room_id )
		if room and flag != room.Moderated:
			room.Moderated = flag
			if flag:
				logger.debug( "%s becoming moderator of room %s", self, room )
				room.add_moderator( self.session_owner )
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
		warnings.warn( "Assuming that clients have seen messages flagged to them." )
		for m in m_ids:
			# TODO: Where does this state belong? Who
			# keeps the message? Passing just the ID assumes
			# that the client can find the message by id.
			self.emit_recvMessageForAttention( usernames, m )
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


def ChatHandlerFactory( socketio_protocol, chatserver=None ):
	session = socketio_protocol.session if hasattr( socketio_protocol, 'session' ) else socketio_protocol
	if session:
		chatserver = component.queryUtility( interfaces.IChatserver ) if not chatserver else chatserver
	if session and chatserver:
		return _ChatHandler( chatserver, session )
	logger.warning( "No session (%s) or chatserver (%s); could not create event handler.", session, chatserver )
