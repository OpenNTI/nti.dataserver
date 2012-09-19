#!/usr/bin/env python

from __future__ import print_function, unicode_literals

import logging
logger = logging.getLogger( __name__ )

from zope import component
from zope import interface

import transaction
import contextlib
import gevent
import types
from Queue import Empty
from gevent.queue import Queue
import time
import socket
import geventwebsocket.exceptions

import pyramid.interfaces
from nti.socketio import interfaces
import nti.dataserver.interfaces as nti_interfaces
from nti.dataserver.sessions import SessionService
from nti.utils import transactions

def _decode_packet_to_session( session, sock, data, doom_transaction=True ):
	try:
		pkts = sock.protocol.decode_multi( data )
	except ValueError:
		# Bad data from the client. This will never work
		if doom_transaction:
			transaction.doom()
		raise

	for pkt in pkts:
		if pkt.msg_type == 0:
			logger.debug( "Killing session %s on receipt of death packet %s from remote client", session, pkt )
			session.kill()
		elif pkt.msg_type == 1:
			sock.send_connect( pkt['data'] )
		elif pkt.msg_type == 2: # heartbeat
			session.heartbeat()
		else:
			#logger.debug( "Session %s received msg %s", session, pkt )
			session.put_server_msg( pkt )

def _safe_kill_session( session, reason='' ):
	logger.debug( "Killing session %s %s", session, reason )
	try:
		session.kill()
	except AttributeError:
		pass
	except:
		logger.exception( "Failed to kill session %s", session )

class BaseTransport(object):
	"""Base class for all transports. Mostly wraps handler class functions."""

	def __init__(self, request):
		"""
		:param request: A :class:`pyramid.request.Request` object.
		"""
		self.request = request

	def kill(self):
		pass

@contextlib.contextmanager
def _using_session_proxy( service, sid  ):
	existing = service.get_proxy_session( sid )
	proxy = _SessionEventProxy()
	if existing is None:
		service.set_proxy_session( sid, proxy )
		try:
			yield proxy
		finally:
			service.set_proxy_session( sid, None )
	else:
		logger.warn( "Session %s already has proxy %s", sid, existing )
		yield proxy

class XHRPollingTransport(BaseTransport):
	component.adapts( pyramid.interfaces.IRequest )
	interface.implements( interfaces.ISocketIOTransport )

	proxy_timeout = 5.0

	def __init__(self, request):
		super(XHRPollingTransport, self).__init__(request)

	def options(self, session):
		rsp = self.request.response
		rsp.content_type = 'text/plain'
		return rsp

	def get(self, session):
		session.clear_disconnect_timeout()
		session_service = component.getUtility( nti_interfaces.IDataserver ).session_manager
		result = None
		try:
			# A dead session will feed us a queue with a None object
			messages = session.get_client_msgs()
			if not messages:
				with _using_session_proxy( session_service, session.session_id ) as session_proxy:
					# Nothing to read right now.
					# The client expects us to block, though, for some time
					# We use our session proxy to both wait
					# and notify us immediately if a new message comes in
					session_proxy.get_client_msg( timeout=self.proxy_timeout )
					# Note that if we get a message via broadcast,
					# our cached session is going to be behind, so it's
					# pointless to try to read from it again. Unfortunately,
					# to avoid duplicate messages, we cannot just send
					# this one to the client (since its still in the session).
					# The simplest thing to do is to immediately return
					# and let the next poll pick up the message. Thus, the return
					# value is ignored and we simply wait
					# TODO: It may be possible to back out of the transaction
					# and retry.

			if not messages:
				raise Empty()
			# If we feed encode_multi None or an empty queue, it raises
			# ValueError.
			# If however, we feed it len() == 1 and that 1 is None,
			# it quietly returns None to us
			result = session.socket.protocol.encode_multi( messages )
		except (Empty,IndexError):
			result = session.socket.protocol.make_noop()

		__traceback_info__ = session, messages, result
		if result is None:
			# Must have pulled a None out of the queue. Which means our
			# session is dead. How to deal with this?
			logger.debug( "Polling got terminal None message. Need to disconnect." )
			result = session.socket.protocol.make_noop()

		response = self.request.response
		response.body = result
		return response

	def _request_body(self):
		return self.request.body


	def post(self, session, response_message=None):
		_decode_packet_to_session( session, session.socket, self._request_body() )
		# The client will expect to re-confirm the session
		# by sending a blank post when it gets an error.
		# Our state must match. However, we cannot do this:
		# session.connection_confirmed = False
		# because our transaction is going to be rolled back

		response = self.request.response
		response.content_type = 'text/plain'
		response.headers['Connection'] = 'close'
		response.body = response_message or session.socket.protocol.make_noop()
		return response

	def _connect_response(self, session):
		response = self.request.response
		response.headers['Connection'] = 'close'
		response.body =  session.socket.protocol.make_connect()
		return response

	def connect(self, session, request_method ):
		if not session.connection_confirmed:
			# This is either the first time in,
			# or we've had an error that we detected. If it was an
			# error, then this could either be a POST
			# or a GET. We can handle GETs the same,
			# POSTs may have data (depending on if the
			# client thinks it should re-connect) that
			# need to be dealt with...
			session.connection_confirmed = True
			if request_method == 'POST' and self.request.content_length:
				response = self.post( session, response_message=session.socket.protocol.make_connect() )
			else:
				response = self._connect_response( session )
			return response

		if request_method == 'POST' and not self.request.content_length:
			# We have a session that WAS confirmed, but the client
			# thinks it is no longer confirmed...we're probably switching transports
			# due to a hard crash of an instance. So treat this
			# like a fresh connection
			response = self._connect_response( session )
			return response

		if request_method in ("GET", "POST", "OPTIONS"):
			try:
				return getattr(self, request_method.lower())(session)
			except ValueError:
				# TODO: What if its binary data?
				logger.debug( "Failed to parse incoming body '%s'", self._request_body(), exc_info=True )
				raise

		raise Exception("No support for the method: " + request_method)


def _catch_all(greenlet):
	def f(*args):
		try:
			greenlet(*args)
		except:
			# Trap and log.
			# We no longer expect to use GreenletExit, so it isn't handled
			# specially.
			logger.exception( "Failed to run greenlet %s", greenlet )
	return f


class _SessionEventProxy(object):
	"""
	Can be used as a session proxy for getting events when
	broadcast messages arrive.

	Functions in a transaction-aware manner for putting client messages
	to avoid them getting put multiple times in the event of retries.
	"""

	def __init__(self):
		# This queue should be unbounded, otherwise we could
		# cause commit problems
		self.client_queue = Queue()

	def get_client_msg(self, **kwargs):
		return self.client_queue.get(**kwargs)
	def put_client_msg( self, msg ):
		transactions.put_nowait( self.client_queue, msg )


# For ease of distinguishing in logs we subclass
class _WebsocketSessionEventProxy(_SessionEventProxy): pass

from nti.dataserver._Dataserver import run_job_in_site as _run_job_in_site

def run_job_in_site( *args, **kwargs ):
	runner = component.queryUtility( nti_interfaces.IDataserverTransactionRunner,
								   default=_run_job_in_site )
	return runner( *args, **kwargs )

class WebsocketTransport(BaseTransport):

	component.adapts( pyramid.interfaces.IRequest )
	interface.implements( interfaces.ISocketIOTransport )

	def __init__( self, request ):
		super(WebsocketTransport,self).__init__(request)
		self.websocket = None

	class WebSocketGreenlet(gevent.Greenlet):

		def __init__( self, run=None, *args, **kwargs ):
			self.ws_operator = run
			gevent.Greenlet.__init__( self, run, *args, **kwargs )

		def ws_ask_to_quit( self ):
			"""
			Use this instead of :meth:`kill` if there's a chance that
			resources might not be cleaned up as the stack unwinds.
			"""
			self.ws_operator.run_loop = False

	class AbstractWebSocketOperator(object):

		def __init__(self, session_id, session_proxy, session_service, websocket ):
			self.session_id = session_id
			self.session_proxy = session_proxy
			self.session_service = session_service
			self.websocket = websocket
			self.run_loop = True

		@_catch_all
		def __call__(self):
			self._run()

		def _run(self):
			raise NotImplementedError()

		def get_session(self):
			return self.session_service.get_session( self.session_id )

		def __repr__( self ):
			return '<%s for %s/%s>' % (self.__class__.__name__, self.session_id, self.websocket)

	class WebSocketSender(AbstractWebSocketOperator):
		message = None

		def _do_send(self):
			message = self.message
			session = self.get_session()
			if session:
				session.get_client_msgs() # prevent buildup
			if message is None:
				_safe_kill_session( session, ' on transfer of None across sending channel' )
				return False
			return True

		def _run(self):
			while self.run_loop:
				self.message = self.session_proxy.get_client_msg()
				logger.info( "Waking up sender for %s", self.message )
				assert isinstance(self.message, (str,types.NoneType)), "Messages should already be encoded as required"
				if not self.run_loop:
					break
				try:
					self.run_loop &= run_job_in_site( self._do_send, retries=10 )
				except transaction.interfaces.TransientError:
					# A problem clearing the queue or getting the session.
					# Generally, these can be ignored, since we'll just try again later
					logger.debug( "Unable to clear session msgs, ignoring", exc_info=True )
					self.run_loop = (self.message is not None)


				if not self.run_loop:
					# Don't send a message if the transactions failed
					# and we're going to break this loop
					break

				try:
					#logger.debug( "Sending session '%s' value '%r'", self.session_id, self.message )
					self.websocket.send(self.message)
				except geventwebsocket.exceptions.FrameTooLargeException:
					logger.warn( "Failed to send message to websocket, %s is too large. Head: %s",
								 len(self.message), self.message[0:50] )
				except socket.error:
					logger.debug( "Stopping sending messages to '%s'", self.session_id, exc_info=True )
					# The session will be killed of its own accord soon enough.
					break

	class WebSocketReader(AbstractWebSocketOperator):
		message = None
		HEARTBEAT_LIFETIME = SessionService.SESSION_HEARTBEAT_TIMEOUT / 2

		# Cache of some stuff from the session
		last_heartbeat_time = 0
		connected = False

		def _do_read(self):
			session = self.get_session( )
			if session is None:
				return False

			self.last_heartbeat_time = session.last_heartbeat_time
			self.connected = session.connected
			if self.message is None:
				# Kill the greenlet
				self.session_proxy.put_client_msg( None )
				# and the session
				_safe_kill_session( session, 'on transfer of None across reading channel' )
				return False

			try:
				_decode_packet_to_session( session, session.socket, self.message, doom_transaction=False )
			except ValueError:
				logger.exception( "Failed to read packets from WS; killing session %s", self.session_id )
				# We don't doom this transaction, we want to commit the death
				# transaction.doom()
				_safe_kill_session( session, 'on failure to read packet from WS' )
				return False

			return True

		def _run(self):
			while self.run_loop:
				self.message = self.websocket.receive()

				# Reduce heartbeat activity from every five seconds to
				# no more often than half of what's needed to keep the session "alive"
				# to cut down on database activity
				# This is tightly coupled to session implementation and lifetime
				if self.message == b"2::" \
				  and self.connected \
				  and self.last_heartbeat_time >= (time.time() - self.HEARTBEAT_LIFETIME):
					continue

				if not self.run_loop:
					break

				# Try for up to 2 seconds to receive this message. If it fails,
				# drop it and wait for the next one. That's better than dieing altogether, right?
				try:
					self.run_loop &= run_job_in_site( self._do_read, retries=20, sleep=0.1 )
				except transaction.interfaces.TransientError:
					logger.exception( "Failed to receive message (%s) from WS; ignoring and continuing %s",
									  self.message[0:50], self.session_id )

	class WebSocketPinger(AbstractWebSocketOperator):

		def __init__( self, *args, **kwargs ):
			super(WebsocketTransport.WebSocketPinger,self).__init__( *args )
			self.ping_sleep = kwargs.get( 'ping_sleep', 5.0 )

		def _do_ping(self):
			session = self.get_session()
			if session and session.connected:
				session.socket.send_heartbeat()
				return True
			return False

		def _do_ping_direct( self ):
			# Short cut everything to reduce DB activity
			try:
				self.websocket.send( b"2::" )
				return True
			except Exception:
				logger.debug( "Stopping sending messages to '%s'", self.session_id, exc_info=True )
				return False

		def _run(self):
			while self.run_loop:
				gevent.sleep( self.ping_sleep )
				if not self.run_loop:
					break
				# FIXME: Make time a config?
				#self.run_loop &= run_job_in_site( self._do_ping, retries=5, sleep=0.1 )
				self.run_loop &= self._do_ping_direct()

	def connect(self, session, request_method, ping_sleep=5.0 ):

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
		session_proxy = _WebsocketSessionEventProxy()
		session_service = component.getUtility( nti_interfaces.IDataserver ).session_manager

		# The three greenlets we spawn are all linked to cleanup() to guarantee
		# that they all die together, and that they all do cleanup when they die
		session_service.set_proxy_session( session_id, session_proxy )

		send_into_ws = self.WebSocketSender( session_id, session_proxy, session_service, websocket )
		read_from_ws = self.WebSocketReader( session_id, session_proxy, session_service, websocket )
		ping = self.WebSocketPinger( session_id, session_proxy, session_service, websocket, ping_sleep=ping_sleep )

		gr1 = self.WebSocketGreenlet.spawn(send_into_ws)
		gr2 = self.WebSocketGreenlet.spawn(read_from_ws)
		heartbeat = self.WebSocketGreenlet.spawn( ping )

		to_cleanup = [gr1, gr2, heartbeat]
		def cleanup(dead_greenlet):
			logger.debug( "Performing cleanup on death of %s/%s", dead_greenlet, session_id )
			if session_service.get_proxy_session( session_id ) is session_proxy:
				logger.debug( "Removing websocket session proxy for %s", session_id )
				session_service.set_proxy_session( session_id, None )

			try:
				to_cleanup.remove( dead_greenlet )
			except ValueError: pass # hmm?
			# When one dies, they all die
			for greenlet in to_cleanup:
				if not greenlet.ready():
					logger.debug( "Asking %s to quit on death of %s", greenlet, dead_greenlet )
					greenlet.ws_ask_to_quit()

		for link in to_cleanup:
			link.link( cleanup )

		# make the section appear connected
		session.connection_confirmed = True
		session.incr_hits()

		return [gr1, gr2, heartbeat]

	def kill( self ):
		try:
			self.websocket.close()
		except Exception:
			logger.exception( "Failed to close websocket." )

class FlashsocketTransport(WebsocketTransport):
	pass
