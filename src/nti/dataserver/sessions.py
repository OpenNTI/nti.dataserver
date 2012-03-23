#!/usr/bin/env python2.7
""" Session distribution and management. """

import logging
logger = logging.getLogger( __name__ )
import warnings
import uuid
import time
import contextlib

import gevent

import zc.queue
from zope import interface
from zope import component
from zope.event import notify

import anyjson as json


# Persistence
from persistent import Persistent
from persistent.list import PersistentList
import BTrees.OOBTree

#import _daemonutils as daemonutils
#import _PubSubDevice
from nti.dataserver import interfaces as nti_interfaces

class SocketSessionEvent(interface.interfaces.ObjectEvent):
	interface.implements(nti_interfaces.ISocketSessionEvent)

class SocketSessionConnectedEvent(SocketSessionEvent):
	interface.implements(nti_interfaces.ISocketSessionConnectedEvent)

class SocketSessionDisconnectedEvent(SocketSessionEvent):
	interface.implements(nti_interfaces.ISocketSessionDisconnectedEvent)

class Session(Persistent):
	"""
	`self.owner`: An attribute for the user that owns the session.
	"""
	interface.implements(nti_interfaces.ISocketSession)

	STATE_NEW = "NEW"
	STATE_CONNECTED = "CONNECTED"
	STATE_DISCONNECTING = "DISCONNECTING"
	STATE_DISCONNECTED = "DISCONNECTED"

	def __init__(self):
		# The session id must be plain ascii for sending across sockets
		self.session_id = uuid.uuid4().hex.encode('ascii')
		self.creation_time = time.time()
		self.client_queue = zc.queue.Queue() # PersistentList() # queue for messages to client
		self.server_queue = zc.queue.Queue() #PersistentList() # queue for messages to server
		self.hits = 0
		self.heartbeats = 0
		self.state = self.STATE_NEW
		self.connection_confirmed = False

		self._owner = None
		self._broadcast_connect = False

		self.last_heartbeat_time = 0

		self._v_session_service = None

	def _p_resolveConflict(self, oldState, savedState, newState ):
		logger.info( 'Conflict to resolve in %s', type(self) )

		for k in newState:
			# cannot count on keys being both places
			if savedState.get(k) != newState.get(k):
				logger.info( "%s\t%s\t%s", k, savedState[k], newState[k] )

		# merge changes to our counters
		for k in ('hits', 'heartbeats'):
			saveDiff = savedState[k] - oldState[k]
			newDiff = newState[k] - oldState[k]
			savedState[k] = oldState[k] + saveDiff + newDiff

		k = 'last_heartbeat_time'
		savedState[k] = max( oldState[k], savedState[k], newState[k] )
		return savedState

	def _get_owner( self ):
		return self._owner
	def _set_owner( self, o ):
		old_owner = self._owner
		self._owner = o
		self.session_service._replace_in_owner_index( self, old_owner )
	owner = property( _get_owner, _set_owner )

	def __str__(self):
		result = ['[session_id=%r' % self.session_id]
		result.append(self.state)
		result.append( 'owner=%s' % self.owner )
		result.append('client_queue[%s]' % len(self.client_queue))
		result.append('server_queue[%s]' % len(self.server_queue))
		result.append('hits=%s' % self.hits)
		result.append('heartbeats=%s' % self.heartbeats)
		result.append( 'confirmed=%s' % self.connection_confirmed )
		result.append( 'id=%s]'% id(self) )
		return ' '.join(result)

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
		if self.hits + 1 == 1:
			self.state = self.STATE_CONNECTED
			self.hits = 1
		if self.connected and self.connection_confirmed and self.owner and not self._broadcast_connect:
			self._broadcast_connect = True
			notify( SocketSessionConnectedEvent( self ) )

	def clear_disconnect_timeout(self):
		# Putting server messages/client messages
		# should not clear this. We wind up writing to session
		# state from background processes, which
		# leads to conflicts.
		self.last_heartbeat_time = time.time()


	def heartbeat(self):
		self.last_heartbeat_time = time.time()

	def kill(self):
		if self.connected:
			# Mark us as disconnecting, and then send notifications
			# (otherwise, it's too easy to recurse infinitely here)
			self.state = self.STATE_DISCONNECTING

			if self.owner:
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


class SessionService(object):
	"""
	Manages the open sessions within the system.

	Keeps a dictionary of `proxy_session` objects that will have
	messages copied to them whenever anything happens to the real
	session.
	"""

	def __init__( self, session_db_cm=None ):
		"""
		:param session_db_cm: A callable to return a context manager which will
			be wrapped around all uses of session_db. Returns a dict-like object:
			`with session_db_cm() as dict_like:`.
		"""
		if session_db_cm:
			self.session_db_cm = session_db_cm
		else:
			session_db = {}
			@contextlib.contextmanager
			def cm():
				yield session_db
			self.session_db_cm = cm

		with self.session_db_cm() as session_db:
			# session_map: session_id -> session
			# session_index: username -> [session_id,...,session_id]
			for k in ('session_map', 'session_index'):
				if not session_db.has_key( k ):
					session_db[k] = BTrees.OOBTree.OOBTree()

		self.proxy_sessions = {}

		env_settings = component.getUtility( nti_interfaces.IEnvironmentSettings )
		self.pub_socket, sub_socket = env_settings.create_pubsub_pair( 'session' )

		def read_incoming():
			while True:
				msgs = sub_socket.recv_multipart()
				# (session_id, function_name, msg_data)
				self._dispatch_message_to_proxy( *msgs )

		gevent.spawn( read_incoming )

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

	def create_session( self, session_class=Session ):
		""" The returned session must not be modified. """
		session = session_class()
		session_id = session.session_id
		with self.session_db_cm() as session_db:
			session_db['session_map'][session_id] = session
		session._v_session_service = self


		def watchdog_session():
			# Some transports make it very hard to detect
			# when a session stops responding (XHR)...it just goes silent.
			# We watch for it to die (since we created it) and cleanup
			# after it...this is a compromise between always
			# knowing it has died and doing the best we can across the cluster
			gevent.sleep( 60 )	# Time? We can detect a dead session no faster than we decide it's dead,
								# which is SESSION_HEARTBEAT_TIMEOUT 
			logger.debug( "Checking status of session %s", session_id )
			sess = self.get_session(session_id) # performs validation, notification
			if sess:
				# still alive, go again
				gevent.spawn( watchdog_session )
			else:
				logger.debug( "Session %s died", session_id )
		gevent.spawn( watchdog_session )

		return session

	def _replace_in_owner_index( self, session, old_owner ):
		with self.session_db_cm() as session_db:
			if old_owner is not None:
				old = session_db['session_index'].get(old_owner)
				if old:
					try:
						old.remove( session.session_id )
						if not old:
							del session_db['session_index'][old_owner]
					except ValueError: pass
			gnu = session_db['session_index'].get( session.owner )
			if not gnu:
				gnu = ()
			session_db['session_index'][session.owner] = PersistentList( [session.session_id] ) + gnu


	def _get_session( self, session_db, session_id, map_name='session_map' ):
		result = session_db[map_name].get( session_id )
		if isinstance( result, Session ):
			result._v_session_service = self
		return result

	SESSION_HEARTBEAT_TIMEOUT = 60 * 2

	def _session_dead( self, session, max_age=SESSION_HEARTBEAT_TIMEOUT ):
		too_old = time.time() - max_age
		return session.last_heartbeat_time < too_old and session.creation_time < too_old

	def _session_cleanup( self, s, session_db, sids=None ):
		""" Cleans up a dead session. """
		# Remove the session from the DB
		try:
			del session_db['session_map'][s.session_id]
		except KeyError: pass

		if sids is None:
			sids = self._get_session( session_db, s.owner, 'session_index' ) or []
		try:
			sids.remove( s.session_id )
		except ValueError: pass

		# Now that the session is unreachable,
		# make sure the session itself knows it's dead
		s.kill()
		# Let any listeners across the cluster also know it
		self._publish_msg( b'session_dead', s.session_id, b"42" )


	def _validated_session( self, s, session_db, sids=None ):
		""" Returns a live session or None """
		if s and self._session_dead( s ):
			self._session_cleanup( s, session_db, sids )
			return None
		return s

	def get_session( self, session_id ):
		with self.session_db_cm() as session_db:
			s = self._validated_session( self._get_session( session_db, session_id ), session_db )
			if s:
				s.incr_hits()
			return s

	def get_sessions_by_owner( self, session_owner ):
		"""
		Returns sessions for the given owner that are reasonably likely
		to be active and alive.
		"""
		with self.session_db_cm() as session_db:
			sids = self._get_session( session_db, session_owner, 'session_index' ) or ()
			result = []
			for s in list(sids): # copy because we mutate
				s = self._validated_session( self._get_session( session_db, s ),
											 session_db,
											 sids )
				if s: result.append( s )
			return result

	def delete_session( self, session_id ):
		with self.session_db_cm() as session_db:
			sess = session_db['session_map'][session_id]
			del session_db['session_map'][session_id]
			del session_db['session_index'][sess.owner] # TODO: Why?
			sess.kill()


	def _put_msg( self, meth, session_id, msg ):
		with self.session_db_cm() as session_db:
			sess = self._get_session( session_db, session_id )
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
			self.pub_socket.send_multipart( [session_id, name, msg_str] )

	def put_server_msg(self, session_id, msg):
		self._put_msg( Session.do_put_server_msg, session_id, msg )
		self._publish_msg( b'put_server_msg', session_id, json.dumps( msg ) )


	def put_client_msg(self, session_id, msg):
		self._put_msg( Session.do_put_client_msg, session_id, msg )
		self._publish_msg( b'put_client_msg', session_id, msg )


	def _get_msgs( self, q_name, session_id ):
		result = None
		with self.session_db_cm() as session_db:
			sess = self._get_session( session_db, session_id )
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
