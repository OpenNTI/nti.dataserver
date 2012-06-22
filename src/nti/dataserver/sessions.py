#!/usr/bin/env python
""" Session distribution and management. """

from __future__ import print_function, unicode_literals

import logging
logger = logging.getLogger( __name__ )
from ZODB import loglevels

import warnings
import uuid
import time
import contextlib

import gevent

import zc.queue
from zope import interface
from zope import component
from zope.event import notify
from zope.annotation import interfaces as an_interfaces
from zope.deprecation import deprecated, deprecate

from nti.zodb import minmax
from nti.utils import transactions

import transaction

import anyjson as json


# Persistence
from persistent import Persistent
import persistent.list
from persistent.mapping import PersistentMapping
import BTrees.OOBTree

from nti.dataserver import interfaces as nti_interfaces
from nti.socketio.interfaces import ISocketSession
from nti.socketio.interfaces import SocketSessionConnectedEvent, SocketSessionDisconnectedEvent

class Session(Persistent):
	"""
	`self.owner`: An attribute for the user that owns the session.
	"""
	interface.implements(ISocketSession,an_interfaces.IAttributeAnnotatable)

	STATE_NEW = "NEW"
	STATE_CONNECTED = "CONNECTED"
	STATE_DISCONNECTING = "DISCONNECTING"
	STATE_DISCONNECTED = "DISCONNECTED"

	connection_confirmed = False
	_owner = None
	_broadcast_connect = False
	state = STATE_NEW

	def __init__(self, session_service=None):
		# The session id must be plain ascii for sending across sockets
		self.session_id = uuid.uuid4().hex.encode('ascii')
		self.creation_time = time.time()
		self.client_queue = zc.queue.Queue() # queue for messages to client
		self.server_queue = zc.queue.Queue() # queue for messages to server

		self._hits = minmax.MergingCounter( 0 )
		self._last_heartbeat_time = minmax.NumericMaximum( 0 )
		self._v_session_service = session_service

	def __eq__( self, other ):
		try:
			return other is self or self.session_id == other.session_id
		except AttributeError:
			return NotImplemented

	def __hash__( self ):
		return hash(self.session_id)

	def _get_owner( self ):
		return self._owner
	def _set_owner( self, o ):
		"""
		Sessions are not allowed to change owners once they have
		one, because that would require making modifications to the owner index
		and potentially other places.
		"""
		if o == self._owner:
			return
		if self._owner is not None:
			raise ValueError( "Cannot change owner of existing session" )

		self._owner = o
		ss = self.session_service
		if ss:
			ss._put_in_owner_index( self )
	owner = property( _get_owner, _set_owner )

	@property
	def last_heartbeat_time(self):
		# Can only read as a property, setting as a property
		# leads to false conflicts
		return self._last_heartbeat_time.value

	def __str__(self):
		result = ['[session_id=%r' % self.session_id]
		result.append(self.state)
		result.append( 'owner=%s' % self.owner )
		result.append( 'client_queue[%s]' % len(self.client_queue))
		result.append( 'server_queue[%s]' % len(self.server_queue))
		result.append( 'hits=%s' % self._hits.value)
		result.append( 'confirmed=%s' % self.connection_confirmed )
		result.append( 'id=%s]'% id(self) )
		return ' '.join(result)

	def __repr__(self):
		result = '<%s/%s/%s at %s>' % (type(self), self.session_id, self.state, id(self))
		return result

	@property
	def connected(self):
		return self.state == self.STATE_CONNECTED

	@property
	def session_service( self ):
		return getattr( self, '_v_session_service', None )

	def incr_hits(self):
		# We don't really need to track this once
		# we're going, and not doing so
		# reduces chances of conflict.

		if self._hits.value + 1 == 1:
			self.state = self.STATE_CONNECTED
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
			self.state = self.STATE_DISCONNECTING

			if self.owner and send_event:
				notify(SocketSessionDisconnectedEvent(self))

			self.do_put_server_msg( None )
			self.do_put_client_msg( None )


	def do_put_server_msg(self, msg):
		self.server_queue.put( msg )

	def do_put_client_msg(self, msg):
		if msg is not None:
			# When we get a message from the client, reset our
			# heartbeat timer. (Don't do this for our termination message)
			self.clear_disconnect_timeout()
		self.client_queue.put( msg )

def _init_session_storage( session_db ):
	for k in ('session_map', 'session_index'):
		if not session_db.has_key( k ):
			session_db[k] = BTrees.OOBTree.OOBTree()

class PersistentSessionServiceStorage(PersistentMapping):
	"""
	A persistent implementation of session storage based on
	a map.
	"""
	interface.implements( nti_interfaces.ISessionServiceStorage )

	def __init__( self ):
		super(PersistentSessionServiceStorage,self).__init__()
		_init_session_storage(self)

	def __getattr__(self, name):
		try:
			return self[name]
		except KeyError: # pragma: no cover
			raise AttributeError(name)

SimpleSessionServiceStorage = PersistentSessionServiceStorage
deprecated('SimpleSessionServiceStorage', "Prefer to use SessionServiceStorage")
deprecated('PersistentSessionServiceStorage', "Prefer to use SessionServiceStorage")

class SessionServiceStorage(persistent.Persistent):
	"""
	A simple persistent implementation of session storage.
	"""
	interface.implements( nti_interfaces.ISessionServiceStorage )
	def __init__( self ):
		self.session_map = BTrees.OOBTree.OOBTree()
		self.session_index = BTrees.OOBTree.OOBTree()

	@deprecate("Access fields directly")
	def __getitem__( self, name ): # pragma: no cover
		"""
		For compatibility with the old PersistentSessionServiceStorage.
		"""
		if name in ('session_map','session_index'):
			return self.__dict__[name]
		raise KeyError( name )


class SessionService(object):
	"""
	Manages the open sessions within the system.

	Keeps a dictionary of `proxy_session` objects that will have
	messages copied to them whenever anything happens to the real
	session.

	This object will look for a utility component of :class:`nti_interfaces.ISessionServiceStorage`
	to provide session storage.

	"""

	interface.implements( nti_interfaces.ISessionService )

	def __init__( self ):
		"""
		"""
		self.proxy_sessions = {}
		self.pub_socket = None
		self.cluster_listener = self._spawn_cluster_listener()

	@property
	def _session_db(self):
		return component.getUtility( nti_interfaces.ISessionServiceStorage )
	@property
	def _session_map(self):
		return self._session_db.session_map
	@property
	def _session_index(self):
		return self._session_db.session_index


	def _spawn_cluster_listener(self):
		env_settings = component.getUtility( nti_interfaces.IEnvironmentSettings )
		self.pub_socket, sub_socket = env_settings.create_pubsub_pair( 'session' )

		def read_incoming():
			while True:
				msgs = sub_socket.recv_multipart()
				# In our background greenlet, we begin and commit
				# transactions around sending messages to
				# the proxy queue. If the proxy is transaction aware,
				# then it must also be waiting in another greenlet
				# on get_client_msg, whereupon it will see this message arrive
				# after we commit (and probably begin its own transaction)
				# Note that the normal _dispatch_message_to_proxy can be called
				# already in a transaction

				try:
					handled = component.getUtility( nti_interfaces.IDataserverTransactionRunner )( lambda: self._dispatch_message_to_proxy( *msgs ), retries=2 )
					#logger.debug( "Dispatched incoming cluster message? %s: %s", handled, msgs )
				except Exception:
					logger.exception( "Failed to dispatch incoming cluster message." )

		return gevent.spawn( read_incoming )

	def _dispatch_message_to_proxy(  self, session_id, function_name, function_arg ):
		handled = False
		proxy = self.get_proxy_session( session_id )
		if hasattr( proxy, function_name ):
			getattr( proxy, function_name )(function_arg)
			handled = True
		elif proxy and function_name == 'session_dead':
			# Kill anything reading from it
			for x in ('put_server_msg', 'put_client_msg'):
				if hasattr( proxy, x ):
					getattr( proxy, x )(None)
			handled = True
		return handled

	def set_proxy_session( self, session_id, session=None ):
		"""
		:param session: Something with `put_server_msg` and `put_client_msg` methods.
			If `None`, then a proxy session for the `session_id` will be removed (if any)
		"""
		if session is not None:
			self.proxy_sessions[session_id] = session
		elif session_id in self.proxy_sessions:
			del self.proxy_sessions[session_id]

	def get_proxy_session( self, session_id ):
		return self.proxy_sessions.get( session_id )

	def create_session( self, session_class=Session, watch_session=True, **kwargs ):
		""" The returned session must not be modified. """
		session = session_class(session_service=self, **kwargs)
		session_id = session.session_id
		self._session_map[session_id] = session

		if watch_session:
			def watchdog_session():
				# Some transports make it very hard to detect
				# when a session stops responding (XHR)...it just goes silent.
				# We watch for it to die (since we created it) and cleanup
				# after it...this is a compromise between always
				# knowing it has died and doing the best we can across the cluster
				gevent.sleep( 60 )	# Time? We can detect a dead session no faster than we decide it's dead,
									# which is SESSION_HEARTBEAT_TIMEOUT
				logger.log( loglevels.TRACE, "Checking status of session %s", session_id )

				try:
					sess = component.getUtility( nti_interfaces.IDataserverTransactionRunner )( lambda: self.get_session(session_id), retries=2 )
				except transaction.interfaces.TransientError:
					# Try again later
					logger.debug( "Trying session poll later", exc_info=True )
					gevent.spawn( watchdog_session )
					return

				if sess:
					# still alive, go again
					gevent.spawn( watchdog_session )
				else:
					logger.debug( "Session %s died", session_id )
			gevent.spawn( watchdog_session )

		return session

	def _put_in_owner_index( self, session ):
		gnu = self._session_index.get( session.owner )
		if gnu is None or isinstance(gnu,persistent.list.PersistentList): #migration
			gnu = BTrees.OOBTree.OOSet( (session.session_id,) )
			self._session_index[session.owner] = gnu
		else:
			gnu.add( session.session_id )

	def _get_session( self, session_db, session_id ):
		result = self._session_map.get( session_id )
		if isinstance( result, Session ):
			result._v_session_service = self
		return result

	SESSION_HEARTBEAT_TIMEOUT = 60 * 2

	def _session_dead( self, session, max_age=SESSION_HEARTBEAT_TIMEOUT ):
		too_old = time.time() - max_age
		return (session.last_heartbeat_time < too_old and session.creation_time < too_old) \
		  or (session.state in (Session.STATE_DISCONNECTING,Session.STATE_DISCONNECTED))

	def _session_cleanup( self, s, session_db, sids=None, send_event=True ):
		""" Cleans up a dead session.

		:param bool send_event: If ``True`` (the default) killing the session broadcasts
			a SocketSessionDisconnectedEvent. Otherwise, no events are sent.

		"""
		# Remove the session from the DB
		try:
			del self._session_map[s.session_id]
		except KeyError: pass # pragma: no cover

		if sids is None:
			sids = self._session_index.get( s.owner ) or ()
		try:
			sids.remove( s.session_id )
		except (KeyError,ValueError,AttributeError): pass

		# Now that the session is unreachable,
		# make sure the session itself knows it's dead
		s.kill(send_event=send_event)
		# Let any listeners across the cluster also know it
		self._publish_msg( b'session_dead', s.session_id, b"42" )


	def _validated_session( self, s, session_db, sids=None, send_event=True ):
		""" Returns a live session or None """
		if s and self._session_dead( s ):
			self._session_cleanup( s, session_db, sids, send_event=send_event )
			return None
		return s

	def get_session( self, session_id ):
		s = self._validated_session( self._get_session( self._session_db, session_id ), self._session_db )
		if s:
			s.incr_hits()
		return s

	def get_sessions_by_owner( self, session_owner ):
		"""
		Returns sessions for the given owner that are reasonably likely
		to be active and alive.
		"""
		sids = self._session_index.get(session_owner) or ()
		result = []
		# For efficiency, and to avoid recursing too deep in the presence of many dead sessions
		# and event listeners for dead sessions that also want to know the live sessions and so call us,
		# we collect all dead sessions before we send any notifications
		dead_sessions = []
		for sid in list(sids): # copy because we mutate -> validated_session -> session_cleanup
			maybe_valid_session = self._get_session( self._session_db, sid )
			valid_session = self._validated_session( maybe_valid_session,
													 self._session_db,
													 sids,
													 send_event=False )
			if valid_session:
				result.append( valid_session )
			elif maybe_valid_session and maybe_valid_session.owner:
				dead_sessions.append( maybe_valid_session )

		for dead_session in dead_sessions:
			notify(SocketSessionDisconnectedEvent( dead_session ) )

		return result

	def delete_sessions( self, session_owner ):
		"""
		Delete all sessions for the given owner (active and alive included)
		"""
		sids = self._session_index.get(session_owner) or ()
		result = []
		for s in list(sids): # copy because we mutate -> delete_session
			self.delete_session(s)
			result.append(s)
		return result

	def delete_session( self, session_id ):
		try:
			sess = self._session_map[session_id]
			del self._session_map[session_id]
		except KeyError:
			return

		session_index = self._session_index.get( sess.owner )
		try:
			session_index.remove( session_id )
		except (ValueError,KeyError,TypeError,AttributeError): pass # pragma: no cover

		sess.kill()


	def _put_msg( self, meth, session_id, msg ):
		sess = self._get_session( self._session_db, session_id )
		if sess:
			meth( sess, msg )

	def _publish_msg( self, name, session_id, msg_str ):
		assert isinstance( name, str ) # Not Unicode, only byte constants

		assert isinstance( session_id, basestring ) # Must be a string of some type now
		if isinstance( session_id, unicode ):
			warnings.warn( "Got unexpected unicode session id", UnicodeWarning, stacklevel=3 )
			session_id = session_id.encode( 'ascii' )

		assert isinstance( msg_str, basestring ) # Must be a string of some type now
		if isinstance( msg_str, unicode ):
			warnings.warn( "Got unexpected unicode value", UnicodeWarning, stacklevel=3 )
			msg_str = msg_str.encode( 'utf-8' )

		# Now notify the cluster of these messages. If the session proxy lives here, in this
		# process, then we can bypass the notification and handle it all in-process.
		# NOTE: This is fairly tricky and fragile because there are a few layers of things
		# going on to make this work correctly for both XHR and WebSockets from any
		# node of the cluster, and to make the WebSockets case non-blocking (gevent). See also
		# socketio-server
		if not self._dispatch_message_to_proxy( session_id, name, msg_str ):
			transactions.do( target=self.pub_socket,
							 call=self.pub_socket.send_multipart,
							 args=([session_id, name, msg_str],) )

	def put_server_msg(self, session_id, msg):
		self._put_msg( Session.do_put_server_msg, session_id, msg )
		self._publish_msg( b'put_server_msg', session_id, json.dumps( msg ) )


	def put_client_msg(self, session_id, msg):
		self._put_msg( Session.do_put_client_msg, session_id, msg )
		self._publish_msg( b'put_client_msg', session_id, msg )


	def _get_msgs( self, q_name, session_id ):
		result = None
		sess = self._get_session( self._session_db, session_id )
		if sess:
			# Reading messages should not reset the timeout.
			# Only the session put_server_msg should do so.
			#sess.clear_disconnect_timeout()
			result = getattr( sess, q_name )
			if result:
				# "pop" them all
				nresult = list(result)
				result._data = ()
				result = nresult
		return result

	def get_client_msgs( self, session_id ):
		"""
		Removes and returns all available client messages from `session_id`,
		otherwise None.
		"""
		return self._get_msgs( 'client_queue', session_id )


	def get_server_msgs( self, session_id ):
		"""
		Removes and returns all available server messages from `session_id`,
		otherwise None.
		"""
		return self._get_msgs( 'server_queue', session_id )
