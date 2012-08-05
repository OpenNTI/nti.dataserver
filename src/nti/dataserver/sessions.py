#!/usr/bin/env python
""" Session distribution and management. """

from __future__ import print_function, unicode_literals

import logging
logger = logging.getLogger( __name__ )
from ZODB import loglevels

import warnings
import time
import anyjson as json

import gevent

from zope import interface
from zope import component
from zope.event import notify

from nti.utils import transactions
import transaction

from nti.dataserver import interfaces as nti_interfaces
from nti.socketio.interfaces import  SocketSessionDisconnectedEvent
from nti.socketio.persistent_session import AbstractSession as Session


@interface.implementer( nti_interfaces.ISessionService )
class SessionService(object):
	"""
	Manages the open sessions within the system.

	Keeps a dictionary of `proxy_session` objects that will have
	messages copied to them whenever anything happens to the real
	session.

	This object will look for a utility component of :class:`nti_interfaces.ISessionServiceStorage`
	to provide session storage.

	"""

	def __init__( self ):
		"""
		"""
		self.proxy_sessions = {}
		self.pub_socket = None
		self.cluster_listener = self._spawn_cluster_listener()

	@property
	def _session_db(self):
		return component.getUtility( nti_interfaces.ISessionServiceStorage )

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
					_ = component.getUtility( nti_interfaces.IDataserverTransactionRunner )( lambda: self._dispatch_message_to_proxy( *msgs ), retries=2 )
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
		if 'owner' not in kwargs:
			raise ValueError( "Neglected to provide owner" )
		session = session_class(**kwargs)
		self._session_db.register_session( session )
		session_id = session.session_id

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

	def _get_session( self, session_id ):
		result = self._session_db.get_session( session_id )
		if isinstance( result, Session ):
			result._v_session_service = self
		return result

	SESSION_HEARTBEAT_TIMEOUT = 60 * 2

	def _is_session_dead( self, session, max_age=SESSION_HEARTBEAT_TIMEOUT ):
		too_old = time.time() - max_age
		return (session.last_heartbeat_time < too_old and session.creation_time < too_old) \
		  or (session.state in (Session.STATE_DISCONNECTING,Session.STATE_DISCONNECTED))

	def _session_cleanup( self, s, send_event=True ):
		"""
		Cleans up a dead session.

		:param bool send_event: If ``True`` (the default) killing the session broadcasts
			a SocketSessionDisconnectedEvent. Otherwise, no events are sent.

		"""
		self._session_db.unregister_session( s )

		# Now that the session is unreachable,
		# make sure the session itself knows it's dead
		s.kill(send_event=send_event)
		# Let any listeners across the cluster also know it
		self._publish_msg( b'session_dead', s.session_id, b"42" )


	def _validated_session( self, s, send_event=True ):
		""" Returns a live session or None """
		if s and self._is_session_dead( s ):
			self._session_cleanup( s, send_event=send_event )
			return None
		return s

	def get_session( self, session_id ):
		s = self._validated_session( self._get_session( session_id ) )
		if s:
			s.incr_hits()
		return s

	def get_sessions_by_owner( self, session_owner ):
		"""
		Returns sessions for the given owner that are reasonably likely
		to be active and alive.
		"""
		maybe_valid_sessions = self._session_db.get_sessions_by_owner( session_owner )
		result = []
		# For efficiency, and to avoid recursing too deep in the presence of many dead sessions
		# and event listeners for dead sessions that also want to know the live sessions and so call us,
		# we collect all dead sessions before we send any notifications
		dead_sessions = []
		for maybe_valid_session in list(maybe_valid_sessions): # copy because we mutate -> validated_session -> session_cleanup
			valid_session = self._validated_session( maybe_valid_session,
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
		:return: All deleted sessions.
		"""
		result = list( self._session_db.get_sessions_by_owner( session_owner ) )
		for s in result:
			self.delete_session(s.id)
		return result

	def delete_session( self, session_id ):
		sess = self._session_db.get_session( session_id )
		self._session_db.unregister_session( sess )
		if sess:
			sess.kill()


	def _put_msg( self, meth, session_id, msg ):
		sess = self._get_session( session_id )
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
		self._put_msg( Session.enqueue_server_msg, session_id, msg )
		self._publish_msg( b'put_server_msg', session_id, json.dumps( msg ) )


	def put_client_msg(self, session_id, msg):
		self._put_msg( Session.enqueue_client_msg, session_id, msg )
		self._publish_msg( b'put_client_msg', session_id, msg )


	def _get_msgs( self, q_name, session_id ):
		result = None
		sess = self._get_session( session_id )
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
