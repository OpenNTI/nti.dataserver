#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
An implementation and methods related to sessions that are store persistently.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import time

from zope import interface
from zope.annotation import IAttributeAnnotatable
from zope.event import notify
import zc.queue

import persistent

from nti.zodb import minmax
from nti.utils.property import dict_read_alias, alias

import nti.socketio.protocol
from nti.socketio import interfaces as sio_interfaces
from nti.socketio.interfaces import SocketSessionConnectedEvent, SocketSessionDisconnectedEvent

import ZODB.POSException

@interface.implementer(sio_interfaces.ISocketSession,IAttributeAnnotatable)
class AbstractSession(persistent.Persistent):
	"""
	Abstract base for persistent session implementations. Because this class
	may be used in a distributed environment, it does not provide
	implementations of :meth:`queue_message_to_client` and :meth:`queue_message_from_client`; your subclass
	will need to decide how to process those locally or remotely. Instead, it provides
	persistent storage queues for these two types of messages, which can be accessed
	using :meth:`enqueue_message_from_client` and :meth:`enqueue_message_to_client`.
	"""

	connection_confirmed = False
	_broadcast_connect = False

	state = None
	session_id = None # The session id must be plain ascii for sending across sockets

	# Things we don't use but others annotate on us
	# TODO: This knowledge is weird
	_session_intid = None # from the intid utility
	originating_site_names = ()

	def __init__(self, owner=None):
		self.creation_time = time.time()
		self.client_queue = zc.queue.CompositeQueue() # queue for messages to client
		self.server_queue = zc.queue.CompositeQueue() # queue for messages to server

		self._hits = minmax.MergingCounter( 0 )
		self._last_heartbeat_time = minmax.NumericMaximum( 0 )
		self.__dict__['owner'] = owner

	def _p_resolveConflict(self, oldState, savedState, newState):
		logger.debug( "Resolving conflict in sessions between %s and %s", savedState, newState )
		# NOTE: The below is wrong. There are two attributes that are assigned by others:

		# So only a few things can change in ways that might
		# conflict.
		# We can ignore:
		# - client_queue, server_queue, _hits, _last_heartbeat_time: handle themselves
		# - creation_time, owner, session_id: immutable
		state = dict(newState)

		# That just leaves connection_confirmed, state, and _broadcast_connect, _session_intid and originating_site_names
		# Connection_confirmed and _broadcast_connect only ever become True, going
		# from being class attributes to instance attributes

		for k in 'connection_confirmed', '_broadcast_connect':
			if k in savedState or k in newState:
				state[k] = True

		# session_intid is set when this object is created and deleted, going from missing to int to None
		# Once it's gone, we should never be resurrected
		if savedState.get( '_session_intid', self ) is None:
			state['_session_intid'] = None

		# Originating_site_names is immutable once set
		if 'originating_site_names' in savedState:
			state['originating_site_names'] = savedState['originating_site_names']

		# The 'state' value goes through a defined sequence. We accept whichever one is
		# farthest along
		ordered_states = [sio_interfaces.SESSION_STATE_NEW,
						  sio_interfaces.SESSION_STATE_CONNECTED,
						  sio_interfaces.SESSION_STATE_DISCONNECTING,
						  sio_interfaces.SESSION_STATE_DISCONNECTED]

		for next_state in reversed(ordered_states):
			if savedState.get( 'state', None ) == next_state or newState.get( 'state', None ) == next_state:
				state['state'] = next_state
				break

		return state

	def __eq__( self, other ):
		try:
			return other is self or self.session_id == other.session_id
		except AttributeError: # pragma: no cover
			return NotImplemented

	def __hash__( self ):
		return hash(self.session_id)

	owner = dict_read_alias('owner')
	id = alias('session_id')

	@property
	def last_heartbeat_time(self):
		# Can only read as a property, setting as a property
		# leads to false conflicts
		return self._last_heartbeat_time.value

	@property
	def socket(self):
		return nti.socketio.protocol.SocketIOSocket( self )

	def __str__(self):
		try:
			result = ['[session_id=%r' % self.session_id]
			result.append(self.state)
			result.append( 'owner=%s' % self.owner )
			result.append( 'client_queue[%s]' % len(self.client_queue))
			result.append( 'server_queue[%s]' % len(self.server_queue))
			result.append( 'hits=%s' % self._hits.value)
			result.append( 'confirmed=%s' % self.connection_confirmed )
			result.append( 'id=%s]'% id(self) )
			return ' '.join(result)
		except (ZODB.POSException.ConnectionStateError,AttributeError):
			# This most commonly (only?) comes up in unit tests when nose defers logging of an
			# error until after the transaction has exited. There will
			# be other log messages about trying to load state when connection is closed,
			# so we don't need to try to log it as well
			return object.__str__(self)

	def __repr__(self):
		try:
			return '<%s/%s/%s at %s>' % (type(self), self.session_id, self.state, id(self))
		except (ZODB.POSException.ConnectionStateError,AttributeError):
			# This most commonly (only?) comes up in unit tests when nose defers logging of an
			# error until after the transaction has exited. There will
			# be other log messages about trying to load state when connection is closed,
			# so we don't need to try to log it as well
			return object.__repr__(self)

	@property
	def connected(self):
		return self.state == sio_interfaces.SESSION_STATE_CONNECTED

	def incr_hits(self):
		# We don't really need to track this once
		# we're going, and not doing so
		# reduces chances of conflict.

		if self._hits.value + 1 == 1:
			self.state = sio_interfaces.SESSION_STATE_CONNECTED
			self._hits.value = 1
		if self.connected and self.connection_confirmed and self.owner and not self._broadcast_connect:
			self._broadcast_connect = True
			notify( SocketSessionConnectedEvent( self ) )

	def clear_disconnect_timeout(self):
		# Putting server messages/client messages
		# should not clear this. We wind up writing to session
		# state from background processes, which
		# leads to conflicts.
		# Directly set the .value, avoiding the property, because
		# the property still causes this object to be considered modified (?)
		self._last_heartbeat_time.set( time.time() )


	def heartbeat(self):
		self.clear_disconnect_timeout()

	def kill(self, send_event=True):
		"""
		Mark this session as disconnected if not already.

		:param bool send_event: If ``True`` (the default) when this method
			actually marks the session as disconnected, and the session had a valid
			owner, an :class:`SocketSessionDisconnectedEvent` will be sent.
		"""
		if self.connected:
			# Mark us as disconnecting, and then send notifications
			# (otherwise, it's too easy to recurse infinitely here)
			self.state = sio_interfaces.SESSION_STATE_DISCONNECTING

			if self.owner and send_event:
				notify(SocketSessionDisconnectedEvent(self))

			self.enqueue_server_msg( None )
			self.enqueue_client_msg( None )


	def enqueue_message_from_client(self, msg):
		if msg is not None:
			# When we get a message from the client, reset our
			# heartbeat timer. (Don't do this for our termination message)
			self.clear_disconnect_timeout()
		self.server_queue.put( msg )

	def enqueue_message_to_client(self, msg):
		self.client_queue.put( msg )

	enqueue_client_msg = enqueue_message_to_client
	enqueue_server_msg = enqueue_message_from_client

	def queue_message_from_client(self, msg):
		raise NotImplementedError() # pragma: no cover

	def queue_message_to_client(self, msg):
		raise NotImplementedError() # pragma: no cover

# for BWC, copy the vocab choices
# as class attributes
map(lambda x: setattr( AbstractSession, 'STATE_' + x, x ), sio_interfaces.ISocketSession['state'].vocabulary.by_token )
AbstractSession.state = sio_interfaces.SESSION_STATE_NEW
