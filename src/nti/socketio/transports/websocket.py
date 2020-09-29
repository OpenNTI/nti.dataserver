#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import time
import socket

from zope import component
from zope import interface

from zope.cachedescriptors.property import Lazy

from ZODB.loglevels import TRACE

import pyramid.interfaces
import transaction.interfaces

import geventwebsocket.exceptions

from nti.dataserver.interfaces import IDataserver

from nti.dataserver.sessions import SessionService

from nti.socketio import interfaces

from nti.socketio.interfaces import ISocketSessionSettings

from ._base import sleep
from ._base import Greenlet
from ._base import catch_all
from ._base import BaseTransport
from ._base import run_job_in_site
from ._base import safe_kill_session
from ._base import SessionEventProxy
from ._base import decode_packet_to_session

# For ease of distinguishing in logs we subclass
class _WebsocketSessionEventProxy(SessionEventProxy):
	pass

class _AbstractWebSocketOperator(object):
	session_owner = ''

	def __init__(self, session_id, session_proxy, session_service, session_originating_site_names, websocket ):
		self.session_id = session_id
		self.session_proxy = session_proxy
		self.session_service = session_service
		self.websocket = websocket
		self.session_originating_site_names = session_originating_site_names
		self.run_loop = True

	@catch_all
	def __call__(self):
		self._run()

	def _run(self):
		raise NotImplementedError()

	def get_session(self):
		return self.session_service.get_session(self.session_id, cleanup=False)

	def __repr__( self ):
		return '<%s for %s%s>' % (self.__class__.__name__, self.session_id, self.session_owner)

class _WebSocketSender(_AbstractWebSocketOperator):
	message = None

	def _do_send(self):
		message = self.message
		session = self.get_session()
		if session:
			session.get_messages_to_client() # prevent buildup in the database
		if message is None or session is None:
			# JZ - 08.2015 - We used to kill our session here, but that would cause a large
			# amount of conflict errors on our session storage, since we kill
			# the same session from the reader.  We eliminate the session
			# killing here, and hope the watchdog will clean up any potential
			# orphans.
			return False
		return True

	def _run(self):
		while self.run_loop:
			sleep()
			# We must get a None here to break out of loop (see reader)
			self.message = self.session_proxy.get_client_msg()

			try:
				self.run_loop &= run_job_in_site( self._do_send, retries=10,
												  site_names=self.session_originating_site_names )
			except transaction.interfaces.TransientError:
				# A problem clearing the queue or getting the session.
				# Generally, these can be ignored, since we'll just try again later
				logger.debug( "Unable to clear session msgs, ignoring", exc_info=True )
				self.run_loop = (self.message is not None)

			if not self.run_loop:
				# Don't send a message if the transactions failed and we're
				# going to break this loop
				break

			try:
				# logger.debug( "Sending session '%s' value '%r'", self.session_id, self.message )
				self.websocket.send(self.message)
			except geventwebsocket.exceptions.FrameTooLargeException:
				logger.warn( "Failed to send message to websocket, %s is too large. Head: %s",
							 len(self.message), self.message[0:50] )
			except socket.error as e:
				logger.log( TRACE, "Stopping sending messages to '%s' on %s", self.session_id, e )
				# The session will be killed of its own accord soon enough.
				break

class _WebSocketReader(_AbstractWebSocketOperator):
	message = None

	# Cache of some stuff from the session
	last_heartbeat_time = 0
	connected = False

	@Lazy
	def heartbeat_update_time(self):
		settings = component.queryUtility(ISocketSessionSettings)
		result = getattr(settings, 'SessionServerHeartbeatUpdateFrequency', None)
		if result is None:
			result = SessionService.session_heartbeat_timeout // 2
		return result

	def _do_read(self):
		session = self.get_session()
		if session is None:
			# Kill the greenlet
			self.session_proxy.queue_message_to_client(None)
			return False

		self.last_heartbeat_time = session.last_heartbeat_time
		self.connected = session.connected
		if self.message is None:
			# Kill the greenlet
			self.session_proxy.queue_message_to_client(None)
			# and the session
			safe_kill_session( session, 'on transfer of None across reading channel' )
			return False

		try:
			decode_packet_to_session( session, session.socket, self.message, doom_transaction=False )
		except ValueError:
			logger.exception( "Failed to read packets from websocket; killing session %s", self.session_id )
			# Kill the greenlet
			self.session_proxy.queue_message_to_client(None)
			# We don't doom this transaction, we want to commit the death
			# transaction.doom()
			safe_kill_session( session, 'on failure to read packet from WS' )
			return False

		return True

	def _run(self):
		try:
			while self.run_loop:
				sleep()
				self.message = self.websocket.receive()

				# This is tightly coupled to session implementation and lifetime. We send
				# pings every 5s.
				if 	  self.message == b"2::" \
				  and self.connected \
				  and self.last_heartbeat_time >= (time.time() - self.heartbeat_update_time):
					continue

				if not self.run_loop:
					break

				# Try for up to 2 seconds to receive this message. If it fails,
				# drop it and wait for the next one. That's better than dying altogether, right?
				try:
					self.run_loop &= run_job_in_site( self._do_read, retries=20, sleep=0.1, site_names=self.session_originating_site_names )
				except transaction.interfaces.TransientError:
					logger.exception( "Failed to receive message (%s) from websocket; ignoring and continuing %s",
									  self.message[0:50], self.session_id )
		finally:
			# Need to make sure we always send a signal to our sender to shut
			# down in case we exist abnormally. Otherwise we'll leak greenlets.
			self.session_proxy.client_queue.put_nowait(None)

class _WebSocketPinger(_AbstractWebSocketOperator):

	def __init__(self, *args, **kwargs):
		super(_WebSocketPinger,self).__init__(*args)
		# Client timeout is currently 60s - this will keep
		# the client from reconnecting.
		ping_sleep = kwargs.get('ping_sleep', None)
		if ping_sleep is None:
			settings = component.queryUtility(ISocketSessionSettings)
			ping_sleep = getattr(settings, 'SessionPingFrequency', 5.0)
		self.ping_sleep = ping_sleep

	def _do_ping( self ):
		try:
			session = self.get_session()
			if session:
				self.websocket.send( b"2::" )
				return True
		except Exception as e:
			logger.debug( "Stopping sending pings to '%s' on %s",
						self.session_id, e )
			logger.exception(e)
		return False

	def _run(self):
		while self.run_loop:
			sleep(self.ping_sleep)
			self.run_loop &= run_job_in_site(self._do_ping, retries=5, sleep=0.1)

class _WebSocketGreenlet(Greenlet):
	"A greenlet that runs a type of :class:`_AbstractWebSocketOperator`"

	def __init__( self, run=None, *args, **kwargs ):
		self.ws_operator = run
		Greenlet.__init__( self, run, *args, **kwargs )

	def ws_ask_to_quit( self ):
		"""
		Use this instead of :meth:`kill` if there's a chance that
		resources might not be cleaned up as the stack unwinds.
		"""
		self.ws_operator.run_loop = False

@component.adapter( pyramid.interfaces.IRequest )
@interface.implementer( interfaces.ISocketIOTransport )
class WebsocketTransport(BaseTransport):

	websocket = None

	def __init__( self, request ):
		super(WebsocketTransport,self).__init__(request)


	def connect(self, session, request_method, ping_sleep=None):
		websocket = self.request.environ['wsgi.websocket']
		websocket.send( session.socket.protocol.make_connect() )
		self.websocket = websocket

		# Messages from the client will only
		# come to exactly this object (sockets!).
		# Messages TO the client could come from any server
		# in the cluster; for that reason, we catch broadcast
		# events using a session proxy and direct them
		# to the client through that queue. Note that this requires
		# events generated on this server to go through the
		# broadcast mechanism too. Last, note that
		# all access to the session object must be in a transaction
		# which loads the session object fresh (if needed)

		session_id = session.session_id
		session_originating_site_names = session.originating_site_names
		session_proxy = _WebsocketSessionEventProxy()
		session_service = component.getUtility( IDataserver ).session_manager

		# The three greenlets we spawn are all linked to cleanup() to guarantee
		# that they all die together, and that they all do cleanup when they die
		session_service.set_proxy_session( session_id, session_proxy )

		send_into_ws = _WebSocketSender( session_id, session_proxy,
										 session_service,
										 session_originating_site_names,
										 websocket )

		read_from_ws = _WebSocketReader( session_id, session_proxy,
										session_service,
										session_originating_site_names,
										websocket )

		ping = _WebSocketPinger( session_id, session_proxy,
								 session_service,
								 session_originating_site_names,
								 websocket,
								 ping_sleep=ping_sleep )

		session_owner = getattr( session, 'owner', '' )
		if session_owner:
			# We only get one shot at setting the thread name (the repr is only read once by gevent/greenlet)
			send_into_ws.session_owner = read_from_ws.session_owner = ping.session_owner = '/' + session_owner

		gr1 = _WebSocketGreenlet.spawn(send_into_ws)
		gr2 = _WebSocketGreenlet.spawn(read_from_ws)
		heartbeat = _WebSocketGreenlet.spawn( ping )

		to_cleanup = [gr1, gr2, heartbeat]
		cleanup = self._make_cleanup(to_cleanup, session_id, session_proxy)
		for link in to_cleanup:
			link.link( cleanup )

		# make the section appear connected
		session.connection_confirmed = True
		session.incr_hits()

		return [gr1, gr2, heartbeat]

	def _make_cleanup(self, to_cleanup, session_id, session_proxy ):
		def cleanup(dead_greenlet):
			logger.log( TRACE, "Performing cleanup on death of %s/%s", dead_greenlet, session_id )
			session_service = component.getUtility( IDataserver ).session_manager
			if session_service.get_proxy_session( session_id ) is session_proxy:
				logger.log( TRACE, "Removing websocket session proxy for %s", session_id )
				session_service.set_proxy_session( session_id, None )

			try:
				to_cleanup.remove( dead_greenlet )
			except ValueError: pass # hmm?
			# When one dies, they all die
			for greenlet in to_cleanup:
				if not greenlet.ready():
					logger.log( TRACE, "Asking %s to quit on death of %s", greenlet, dead_greenlet )
					greenlet.ws_ask_to_quit()

		return cleanup

	def kill( self ):
		try:
			self.websocket.close()
		except Exception:
			logger.exception( "Failed to close websocket." )

class FlashsocketTransport(WebsocketTransport):
	pass
