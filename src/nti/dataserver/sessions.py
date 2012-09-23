#!/usr/bin/env python
""" Session distribution and management. """

from __future__ import print_function, unicode_literals

import logging
logger = logging.getLogger( __name__ )
from ZODB import loglevels

import warnings
import time
import anyjson as json
import zlib
import gevent

from zope import interface
from zope import component
from zope.event import notify

from nti.utils import transactions
import transaction

from nti.dataserver import interfaces as nti_interfaces
from nti.socketio.interfaces import  SocketSessionDisconnectedEvent
from nti.socketio.persistent_session import AbstractSession as Session
from nti.dataserver.interfaces import SiteNotInstalledError

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

	_redis = None

	def __init__( self ):
		"""
		"""
		self.proxy_sessions = {}
		self.pub_socket = None
		# Note that we have no way to close these greenlets. We depend
		# on GC of this object to let them die when the last refs to
		# us do.
		self._redis = self._get_redis()
		self.cluster_listener = self._spawn_cluster_listener()
		self._watching_sessions = set()
		self._session_watchdog = self._spawn_session_watchdog()


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
				# NOTE: that the normal _dispatch_message_to_proxy can be called
				# already in a transaction
				# NOTE: We do not do this in a site (to reduce DB connections), so the proxy listeners need to
				# be very limited in what they do

				try:
					#_ = component.getUtility( nti_interfaces.IDataserverTransactionRunner )( lambda: self._dispatch_message_to_proxy( *msgs ), retries=2 )
					transaction.begin()
					_ = self._dispatch_message_to_proxy( *msgs )
					transaction.commit()
				except Exception:
					logger.exception( "Failed to dispatch incoming cluster message." )

		return gevent.spawn( read_incoming )

	def _spawn_session_watchdog( self ):
		def watchdog_sessions():
			while True:
				# Some transports make it very hard to detect
				# when a session stops responding (XHR)...it just goes silent.
				# We watch for it to die (since we created it) and cleanup
				# after it...this is a compromise between always
				# knowing it has died and doing the best we can across the cluster
				gevent.sleep( 60 )	# Time? We can detect a dead session no faster than we decide it's dead,
									# which is SESSION_HEARTBEAT_TIMEOUT
				watching_sessions = list(self._watching_sessions)

				# TODO: With the heartbeats in redis, we can check for valid sessions there.
				# Only for invalid sessions will we have to hit the DB
				try:
					# In the past, we have done this by having a single greenlet per
					# session_id. While this was convenient and probably not too heavy weight from a greenlet
					# perspective, there are some indications that so many small transactions was
					# a net loss as far as the DB goes. A few bigger transactions are more efficient, to a point
					# although there is a higher risk of conflict
					sessions = component.getUtility( nti_interfaces.IDataserverTransactionRunner )( lambda: {sid: self.get_session(sid) for sid in watching_sessions}, retries=5, sleep=0.1 )
				except transaction.interfaces.TransientError:
					# Try again later
					logger.debug( "Trying session poll later", exc_info=True )
					continue
				except SiteNotInstalledError:
					logger.debug( "Site setup not ready; trying to poll later" ) # Happens if startup takes too long, e.g., while downloading index data
					continue

				for sid, sess in sessions.items():
					if sess is None:
						logger.debug( "Session %s died", sid )
						self._watching_sessions.discard( sid )
		return gevent.spawn( watchdog_sessions )

	def _dispatch_message_to_proxy(  self, session_id, function_name, function_arg ):
		handled = False
		proxy = self.get_proxy_session( session_id )
		if hasattr( proxy, function_name ):
			getattr( proxy, function_name )(function_arg)
			handled = True
		elif proxy and function_name == 'session_dead':
			# Kill anything reading from it
			for x in ('queue_message_from_client', 'queue_message_to_client'):
				if hasattr( proxy, x ):
					getattr( proxy, x )(None)
			handled = True
		return handled

	def set_proxy_session( self, session_id, session=None ):
		"""
		:param session: Something with `queue_message_from_client` and `queue_message_to_client` methods.
			If `None`, then a proxy session for the `session_id` will be removed (if any)
		"""
		if session is not None:
			self.proxy_sessions[session_id] = session
		elif session_id in self.proxy_sessions:
			del self.proxy_sessions[session_id]

	def get_proxy_session( self, session_id ):
		return self.proxy_sessions.get( session_id )

	def create_session( self, session_class=Session, watch_session=True, drop_old_sessions=True, **kwargs ):
		"""
		The returned session must not be modified.

		:param bool drop_old_sessions: If ``True`` (the default) then we will proactively look
			for sessions for the session owner in excess of some number or some age and automatically kill them, keeping
			a limit on the outstanding sessions the owner can have.
			TODO: This may force older clients off the connection? Which may make things worse?
		:param unicode owner: The session owner.
		:param kwargs: All the remaining arguments are passed to the session constructor.

		"""
		if 'owner' not in kwargs:
			raise ValueError( "Neglected to provide owner" )

		session = session_class(**kwargs)
		self._session_db.register_session( session )

		if drop_old_sessions:
			outstanding = self.get_sessions_by_owner( session.owner )
			if len(outstanding) > 5: # TODO: Param for this?
				# Sort them from oldest to newest
				outstanding = sorted(outstanding, key=lambda x: x.creation_time)
				# split the five newest from all the older ones
				#newest = outstanding[-5:]
				older = outstanding[:-5]
				# Kill all the old ones
				for s in older:
					self._session_cleanup( s, send_event=False )
				for s in older:
					notify( SocketSessionDisconnectedEvent( s ) )

		session_id = session.session_id
		if watch_session:
			self._watching_sessions.add( session_id )

		return session

	def _get_session( self, session_id ):
		"""
		Gets a session object without any validation.
		"""
		result = self._session_db.get_session( session_id )
		if isinstance( result, Session ):
			result._v_session_service = self
		return result

	SESSION_HEARTBEAT_TIMEOUT = 60 * 2

	def _is_session_dead( self, session, max_age=SESSION_HEARTBEAT_TIMEOUT ):
		too_old = time.time() - max_age
		last_heartbeat_time = self.get_last_heartbeat_time( session.session_id, session )
		return (last_heartbeat_time < too_old and session.creation_time < too_old) \
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

	def _get_redis( self ):
		if self._redis is None:
			self._redis = component.queryUtility( nti_interfaces.IRedisClient, default=0 )
			if self._redis:
				logger.info( "Using redis for session storage" )
			else:
				logger.warn( "Using the database for session storage" )
		return self._redis

	def _put_msg_to_redis( self, queue_name, msg ):
		self._redis.pipeline().rpush( queue_name, msg ).expire( queue_name, self.SESSION_HEARTBEAT_TIMEOUT * 2 ).execute()

	def _put_msg( self, meth, q_name, session_id, msg ):
		sess = self._get_session( session_id )

		if self._get_redis() and sess:
			queue_name = 'sessions.' + session_id + '.' + q_name
			# TODO: Probably need to add timeouts here
			if meth == Session.enqueue_message_from_client and msg is not None:
				# Since we don't call it anymore, we need to handle the timeout
				# ourself...except, we can avoid a DB store if we let
				# the normal heartbeat do this
				#sess.clear_disconnect_timeout()
				pass
			if msg is None:
				msg = ''
			else:
				msg = zlib.compress( msg )
			# We wind up with a lot of these data managers for a given transaction (e.g., one for every
			# message to every session). We really would like to coallesce these into one, which we
			# can do with some work
			transactions.do( target=self,
							 call=self._put_msg_to_redis,
							 args=(queue_name, msg,) )
		elif sess:
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

	def queue_message_from_client(self, session_id, msg):
		self._put_msg( Session.enqueue_message_from_client, 'server_queue', session_id, msg )
		self._publish_msg( b'queue_message_from_client', session_id, json.dumps( msg ) )


	def queue_message_to_client(self, session_id, msg):
		self._put_msg( Session.enqueue_message_to_client, 'client_queue', session_id, msg )
		self._publish_msg( b'queue_message_to_client', session_id, msg )


	def _get_msgs( self, q_name, session_id ):
		result = None
		if self._get_redis():
			queue_name = 'sessions.' + session_id + '.' + q_name
			# atomically read the current messages and then clear the state of the queue.
			msgs, _ = self._redis.pipeline().lrange( queue_name, 0, -1 ).delete(  queue_name ).execute()
			# If the transaction aborts, got to put these back so they don't get lost
			if msgs: # lpush requires at least one message
				def after_commit( success ):
					if success:
						return
					logger.info( "Pushing messages back onto %s on abort", queue_name )
					msgs.reverse()
					self._redis.lpush( queue_name, *msgs )
				transaction.get().addAfterCommitHook( after_commit )
				# unwrap None encoding, decompress strings. The result is a generator
				# because it's very rarely actually used
				result = (None if not x else zlib.decompress(x) for x in msgs)
			else:
				result = () # empty tuple for cheap
		else:
			sess = self._get_session( session_id )
			if sess:
				# Reading messages should not reset the timeout.
				# Only the session queue_message_from_client should do so.
				#sess.clear_disconnect_timeout()
				result = getattr( sess, q_name )
				if result:
					# "pop" them all
					nresult = list(result)
					result._data = ()
					result = nresult
			return result

	def get_messages_to_client( self, session_id ):
		"""
		Removes and returns all available client messages from `session_id`,
		otherwise None.
		"""
		return self._get_msgs( 'client_queue', session_id )

	def get_messages_from_client( self, session_id ):
		"""
		Removes and returns all available server messages from `session_id`,
		otherwise None.
		"""
		return self._get_msgs( 'server_queue', session_id )

	# Redirect heartbeats through redis if possible. Note this is scuzzy and not clean

	def _heartbeat_key( self, session_id ):
		return 'sessions.' + session_id + '.heartbeat'

	def clear_disconnect_timeout(self, session_id ):
		if self._get_redis():
			# Note that we don't make this transactional. The fact that we got a message
			# from a client is a good-faith indication the client is still around.
			key_name = self._heartbeat_key( session_id )
			self._redis.pipeline( ).set( key_name, time.time() ).expire( key_name, self.SESSION_HEARTBEAT_TIMEOUT * 2 ).execute()
		else:
			sess = self._get_session( session_id )
			if sess and hasattr( sess, '_last_heartbeat_time' ):
				sess._last_heartbeat_time.set( time.time() )


	def get_last_heartbeat_time(self, session_id, session=None ):
		result = 0
		if self._get_redis():
			# TODO: This gets called a fair amount. Do we need to cache?
			key_name = self._heartbeat_key( session_id )
			val = self._redis.get( key_name )
			result = float( val or '0' )
		else:
			sess = session or self._get_session( session_id )
			if sess and hasattr( sess, '_last_heartbeat_time' ):
				assert sess.session_id == session_id
				result = sess._last_heartbeat_time.value
		return result
