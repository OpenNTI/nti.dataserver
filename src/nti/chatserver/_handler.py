#!/usr/bin/env python
""" Chatserver functionality. """
from __future__ import print_function, unicode_literals, absolute_import

__docformat__ = "restructuredtext en"

import logging
logger = logging.getLogger( __name__ )

import os
import warnings

from nti.externalization.interfaces import StandardExternalFields as XFields
from nti.chatserver import interfaces as chat_interfaces
from nti.socketio import interfaces as sio_interfaces
from nti.dataserver import interfaces as nti_interfaces
from nti.zodb import interfaces as zodb_interfaces

# FIXME: Break this dependency

from nti.dataserver import users
from nti.dataserver import authorization_acl as auth_acl


from persistent import Persistent
from persistent.mapping import PersistentMapping

from zope import interface
from zope.interface.common import mapping as imapping
from zope import component
from zope import schema
from zope.cachedescriptors.property import Lazy


from nti.utils.sets import discard as _discard
from nti.zodb.tokenbucket import PersistentTokenBucket


from ._metaclass import _ChatObjectMeta
from . import interfaces
from . import MessageFactory as _


EVT_ENTERED_ROOM = 'chat_enteredRoom'
EVT_EXITED_ROOM = 'chat_exitedRoom'
EVT_POST_MESSOGE = 'chat_postMessage'
EVT_RECV_MESSAGE = 'chat_recvMessage'



class MessageRateExceeded(sio_interfaces.SocketEventHandlerClientError):
	"""
	Raised when a user is attempting to post too many chat messages too quickly.
	"""

	i18n_message = _("You are trying to send too many chat messages too quickly. Please wait and try again.")

class IChatHandlerSessionState(interface.Interface):
	rooms_i_moderate = schema.Object( imapping.IFullMapping,
									  title="Mapping of rooms I moderate" )
	message_post_rate_limit = schema.Object( zodb_interfaces.ITokenBucket,
											 title="Take one token for every message you attempt to post." )

@interface.implementer(IChatHandlerSessionState)
@component.adapter(sio_interfaces.ISocketSession)
class _ChatHandlerSessionState(Persistent):
	"""
	An annotation for sessions to store the state a chat handler likes to have,
	since chat handlers have no state for longer than a single event.

	.. caution:: Recall that relatively speaking annotations are expensive and probably
		not suited to writing something for every incoming message (that creates
		lots of database transaction traffic) such as would potentially be needed
		for persistent rate-based throttling. On the other hand, if you're going to be
		writing something anyway (e.g., you have successfully posted a message to a chat
		room) then adding something here is probably not a problem.
	"""

	@Lazy
	def rooms_i_moderate(self):
		return PersistentMapping()

	@Lazy
	def message_post_rate_limit(self):
		# This is sure to be heavily tweaked over time. Initially, we
		# start with one limit for all users: In any given 60 second period,
		# you can post 30 messages (one every other second). You can burst
		# faster than that, up to a max of 30 incoming messages. If you aren't
		# ever idle, you can sustain a rate of one message every two seconds.
		return PersistentTokenBucket(30, 2.0)

from zope.annotation import factory as an_factory
_ChatHandlerSessionStateFactory = an_factory(_ChatHandlerSessionState)


@interface.implementer(chat_interfaces.IChatEventHandler)
@component.adapter(nti_interfaces.IUser,sio_interfaces.ISocketSession,chat_interfaces.IChatserver)
class _ChatHandler(object):
	"""
	Class to handle each of the messages sent to or from a client in the ``chat`` prefix.

	As a socket event handler, instances of this class are created
	fresh to handle every event and thus have no persistent state. This
	objects uses the strategy of adapting the session to storage using
	annotations if necessary to store additional state.
	"""

	__metaclass__ = _ChatObjectMeta
	__emits__ = ('recvMessageForAttention', 'presenceOfUserChangedTo',
				 'data_noticeIncomingChange', 'failedToEnterRoom' )
	_session_consumer_args_search_ = ('nti.chatserver.meeting','nti.chatserver.messageinfo')


	event_prefix = 'chat' #: the namespace of events we handle

	chatserver = None
	session_user = None
	session = None

	# recall that public methods correspond to incomming events

	def __init__( self, *args):
		# For backwards compat, we accept either two args or three, as specified
		# in our adapter contract
		if len( args ) == 3:
			self.session_user = args[0]
			self.session = args[1]
			self.chatserver = args[2]
		else:
			assert len(args) == 2
			warnings.warn( "Use an adapter", DeprecationWarning, stacklevel=2 )
			self.chatserver = args[0]
			self.session = args[1]
			self.session_user = users.User.get_user( self.session.owner )

	def __reduce__(self):
		raise TypeError()

	def __str__( self ):
		return "%s(%s %s)" % (self.__class__.__name__, self.session.owner, self.session.session_id)


	def _get_chatserver(self):
		return self.chatserver or component.queryUtility( interfaces.IChatserver )
	def _set_chatserver( self, cs ):
		self.chatserver = cs
	_chatserver = property(_get_chatserver, _set_chatserver )

	def postMessage( self, msg_info ):
		# Ensure that the sender correctly matches.
		msg_info.Sender = self.session.owner
		msg_info.sender_sid = self.session.session_id
		result = True
		# Rate limit all incoming chat messages
		state = IChatHandlerSessionState(self.session)
		if not state.message_post_rate_limit.consume():
			if 'DATASERVER_SYNC_CHANGES' in os.environ: # hack for testing
				logger.warn( "Allowing message rate for %s to exceed throttle %s during integration testings.", self, state.message_post_rate_limit )
			else:
				raise MessageRateExceeded()


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
			user = self.session_user
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

@interface.implementer(chat_interfaces.IChatEventHandler)
@component.adapter(nti_interfaces.ICoppaUserWithoutAgreement,sio_interfaces.ISocketSession,chat_interfaces.IChatserver)
def ChatHandlerNotAvailable(*args):
	"""
	A factory that produces ``None``, effectively disabling chat.
	"""
	return None

@interface.implementer(sio_interfaces.ISocketEventHandler)
def ChatHandlerFactory( socketio_protocol, chatserver=None ):
	session = socketio_protocol.session if hasattr( socketio_protocol, 'session' ) else socketio_protocol
	if session:
		chatserver = component.queryUtility( interfaces.IChatserver ) if not chatserver else chatserver
		user = users.User.get_user( session.owner )
	if session and chatserver and user:
		handler = component.queryMultiAdapter( (user, session, chatserver), chat_interfaces.IChatEventHandler )
		return handler
	logger.warning( "No session (%s) or chatserver (%s) or user (%r=%s); could not create event handler.",
					session, chatserver, getattr( session, 'owner', None ), user )
