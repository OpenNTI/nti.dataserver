#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
An implementation and methods related to sessions that are store persistently.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import time

from zope import interface
from zope.event import notify

from zope.annotation import IAttributeAnnotatable

from zope.cachedescriptors.property import cachedIn

from ZODB.POSException import ConnectionStateError

from nti.externalization.representation import WithRepr

from nti.property.property import alias
from nti.property.property import dict_read_alias

from nti.schema.eqhash import EqHash

from nti.zodb import minmax

from nti.zodb.persistentproperty import PersistentPropertyHolder

from .protocol import SocketIOSocket

from .interfaces import SESSION_STATE_NEW
from .interfaces import SESSION_STATE_CONNECTED
from .interfaces import SESSION_STATE_DISCONNECTED
from .interfaces import SESSION_STATE_DISCONNECTING

from .interfaces import ISocketSession
from .interfaces import ISocketIOSocket
from .interfaces import SocketSessionConnectedEvent
from .interfaces import SocketSessionDisconnectedEvent

_state_progression = [SESSION_STATE_NEW,
					  SESSION_STATE_CONNECTED,
					  SESSION_STATE_DISCONNECTING,
					  SESSION_STATE_DISCONNECTED]
_reversed_state_progression = reversed(_state_progression)

@interface.implementer(ISocketSession, IAttributeAnnotatable) # pylint:disable=R0921
@EqHash('session_id')
@WithRepr
class AbstractSession(PersistentPropertyHolder):
	"""
	Abstract base for persistent session implementations. Because this
	class may be used in a distributed environment, it does not
	provide implementations of :meth:`queue_message_to_client` and
	:meth:`queue_message_from_client`; your subclass will need to
	decide how to process those locally or remotely.
	"""

	heartbeat_is_transactional = True

	connection_confirmed = False
	_broadcast_connect = False

	state = None
	session_id = None # The session id must be plain ascii for sending across sockets

	# Things we don't use but others annotate on us
	# TODO: This knowledge is weird
	_session_intid = None # from the intid utility
	originating_site_names = ()

	last_heartbeat_time = minmax.NumericPropertyDefaultingToZero( str('_last_heartbeat_time'),
																  minmax.NumericMaximum,
																  as_number=True )

	owner = dict_read_alias('owner') # XXX: JAM: What was I thinking here? What does this save?
	id = alias('session_id')

	creation_time = None
	createdTime = alias('creation_time')

	def __init__(self, owner=None):
		self.creation_time = time.time()

		self._hits = minmax.MergingCounter( 0 )
		self.__dict__['owner'] = owner.decode( 'utf-8' ) if isinstance( owner, str ) else owner

	def _p_resolveConflict(self, oldState, savedState, newState):
		logger.debug( "Resolving conflict in sessions between %s and %s", savedState, newState )
		# NOTE: The below is wrong. There are two attributes that are assigned by others:

		# So only a few things can change in ways that might
		# conflict.
		# We can ignore:
		# - _hits, _last_heartbeat_time: handle themselves
		# - creation_time, owner, session_id: immutable
		state = dict(newState)

		# That just leaves connection_confirmed, state, and _broadcast_connect, _session_intid and originating_site_names
		# Connection_confirmed and _broadcast_connect only ever become True, going
		# from being class attributes to instance attributes

		for k in 'connection_confirmed', '_broadcast_connect':
			if k in savedState or k in newState:
				state[str(k)] = True

		# session_intid is set when this object is created and deleted, going from missing to int to None
		# Once it's gone, we should never be resurrected
		if savedState.get( '_session_intid', self ) is None:
			state[str('_session_intid')] = None

		# Originating_site_names is immutable once set
		if 'originating_site_names' in savedState:
			state[str('originating_site_names')] = savedState['originating_site_names']

		# The 'state' value goes through a defined sequence. We accept whichever one is
		# farthest along
		for next_state in _reversed_state_progression:
			if savedState.get( 'state', None ) == next_state or newState.get( 'state', None ) == next_state:
				state[str('state')] = next_state
				break

		return state

	@cachedIn('_v_socket')
	def socket(self):
		return SocketIOSocket( self )

	def __conform__( self, iface ):
		# Shortcut for using ISocketIOSocket(session) to return a socket;
		# currently identical to session.socket, but useful in the future
		# for flexibility
		if ISocketIOSocket == iface:
			return self.socket
		return None

	def __str__(self):
		try:
			result = ['[session_id=%r' % self.session_id]
			result.append(self.state)
			result.append( 'owner=%s' % self.owner )
			result.append( 'hits=%s' % self._hits.value)
			result.append( 'confirmed=%s' % self.connection_confirmed )
			result.append( 'id=%s]'% id(self) )
			return ' '.join(result)
		except (ConnectionStateError, AttributeError, KeyError):
			# This most commonly (only?) comes up in unit/functional
			# tests when nose (or pyramid_debugtoolbar) defers logging
			# of an error until after the transaction has exited.
			# There will be other log messages about trying to load
			# state when connection is closed, so we don't need to try
			# to log it as well.
			return object.__str__(self)

	@property
	def connected(self):
		return self.state == SESSION_STATE_CONNECTED

	def incr_hits(self):
		# We don't really need to track this once
		# we're going, and not doing so
		# reduces chances of conflict.

		if self._hits.value + 1 == 1:
			self.state = SESSION_STATE_CONNECTED
			self._hits.value = 1
		if 	self.connected and self.connection_confirmed and self.owner \
			and not self._broadcast_connect:
			self._broadcast_connect = True
			notify( SocketSessionConnectedEvent( self ) )

	def clear_disconnect_timeout(self):
		# Putting server messages/client messages
		# should not clear this. We wind up writing to session
		# state from background processes, which
		# leads to conflicts.
		# Directly set the .value, avoiding the property, because
		# the property still causes this object to be considered modified (?)
		self.last_heartbeat_time = time.time()

	def heartbeat(self):
		self.clear_disconnect_timeout()

	def kill(self, send_event=True):
		"""
		Mark this session as disconnected if not already. Many listeners
		expect to get a None message when the session disconnects;
		if the subclass has provided implementations of :meth:`queue_message_from_client`
		and :meth:`queue_message_to_client`, then None will be passed to those methods.

		:param bool send_event: If ``True`` (the default) when this method
			actually marks the session as disconnected, and the session had a valid
			owner, an :class:`SocketSessionDisconnectedEvent` will be sent.
		"""
		if not self.connected:
			return

		# Mark us as disconnecting, and then send notifications
		# (otherwise, it's too easy to recurse infinitely here)
		self.state = SESSION_STATE_DISCONNECTING

		if self.owner and send_event:
			notify(SocketSessionDisconnectedEvent(self))

		for m in self.queue_message_to_client, self.queue_message_from_client:
			try:
				m(None)
			except NotImplementedError:
				pass

	def queue_message_from_client(self, msg):
		raise NotImplementedError() # pragma: no cover

	def queue_message_to_client(self, msg):
		raise NotImplementedError() # pragma: no cover

# for BWC, copy the vocab choices
# as class attributes
map(lambda x: setattr( AbstractSession, str('STATE_' + x), x ),
	ISocketSession['state'].vocabulary.by_token )
AbstractSession.state = SESSION_STATE_NEW
