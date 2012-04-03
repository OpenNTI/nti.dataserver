#!/usr/bin/env python

from __future__ import print_function, unicode_literals

import logging
logger = logging.getLogger( __name__ )

from zope import component
from zope import interface

import transaction
import gevent
from Queue import Empty
from gevent.queue import Queue
import socket

import pyramid.interfaces
from nti.socketio import interfaces
import nti.dataserver.interfaces as nti_interfaces


def _decode_packet_to_session( session, sock, data ):
	try:
		pkts = sock.protocol.decode_multi( data )
	except ValueError:
		# Bad data from the client. This will never work
		transaction.doom()
		raise

	for pkt in pkts:
		if pkt.msg_type == 0:
			session.kill()
		elif pkt.msg_type == 1:
			sock.send_connect( pkt['data'] )
		elif pkt.msg_type == 2: # heartbeat
			session.heartbeat()
		else:
			session.put_server_msg( pkt )

class BaseTransport(object):
	"""Base class for all transports. Mostly wraps handler class functions."""

	def __init__(self, request):
		"""
		:param request: A :class:`pyramid.request.Request` object.
		"""
		self.request = request

	def kill(self):
		pass



class XHRPollingTransport(BaseTransport):
	component.adapts( pyramid.interfaces.IRequest )
	interface.implements( interfaces.ISocketIOTransport )

	def __init__(self, request):
		super(XHRPollingTransport, self).__init__(request)

	def options(self, session):
		rsp = self.request.response
		rsp.content_type = 'text/plain'
		return rsp

	def get(self, session):
		session.clear_disconnect_timeout()
		session_proxy = _SessionEventProxy()
		session_service = component.getUtility( nti_interfaces.IDataserver ).session_manager
		existing_proxy = "did not check"

		try:
			# A dead session will feed us a None object
			# whereupon...we blow up...
			messages = session.get_client_msgs()
			if not messages:
				existing_proxy = session_service.get_proxy_session( session.session_id )
				if existing_proxy is None:
					# On the chance that we're already polling
					# for this session in this server, don't replace the proxy
					# (This is 'thread'-safe because we're greenlets)
					session_service.set_proxy_session( session.session_id, session_proxy )

					# Nothing to read right now.
					# The client expects us to block, though, for some time
					# We use our session proxy to both wait
					# and notify us immediately if a new message comes in
					session_proxy.get_client_msg( timeout=5.0 )
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
			message = session.socket.protocol.encode_multi( messages )
		except (Empty,IndexError):
			message = session.socket.protocol.make_noop()
		finally:
			if existing_proxy is None:
				session_service.set_proxy_session( None )

		response = self.request.response
		response.body = message
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
				response = self.request.response
				response.headers['Connection'] = 'close'
				response.body =  session.socket.protocol.make_connect()

			return response

		if request_method == 'POST' and not self.request.content_length:
			# We have a session that WAS confirmed, but the client
			# thinks it is no longer confirmed...we're probably switching transports
			# due to a hard crash of an instance. So treat this
			# like a fresh connection
			response = self.request.response
			response.headers['Connection'] = 'close'
			response.body =  session.socket.protocol.make_connect( )
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
	def f():
		try:
			greenlet()
		except:
			# Trap and log.
			logger.exception( "Failed to run greenlet %s", greenlet )
	return f


# def _retrying_job(func, retries):
# 	note = func.__doc__
# 	if note:
# 		note = note.split('\n', 1)[0]
# 	else:
# 		note = func.__name__

# 	for i in xrange(retries + 1):
# 		t = manager.begin()
# 		if i:
# 			t.note("%s (retry: %s)" % (note, i))
# 		else:
# 			t.note(note)

# 		try:
# 			func(t)
# 			t.commit()
# 		except transaction.interfaces.TransientError:
# 			t.abort()
# 		else:
# 			break

class _SessionEventProxy(object):
	"""
	Can be used as a session proxy for getting events when
	broadcast messages arrive.
	"""
	def __init__(self):
		self.client_queue = Queue()

	def get_client_msg(self, **kwargs):
		return self.client_queue.get(**kwargs)
	def put_client_msg( self, msg ):
		self.client_queue.put_nowait( msg )

class WebsocketTransport(BaseTransport):

	component.adapts( pyramid.interfaces.IRequest )
	interface.implements( interfaces.ISocketIOTransport )

	def __init__( self, request ):
		super(WebsocketTransport,self).__init__(request)
		self.websocket = None

	def connect(self, *args, **kwargs):

		websocket = self.request.environ['wsgi.websocket']
		websocket.send("1::")
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
		# TODO: Create Greenlet subclass that handles transactions
		# and the standard loop and use that here.
		session_id = args[0].session_id
		session_proxy = _SessionEventProxy()
		session_service = component.getUtility( nti_interfaces.IDataserver ).session_manager
		context_manager_callable = component.queryUtility( nti_interfaces.IDataserverTransactionContextManager,
														   default=getattr( self.request, 'context_manager_callable', None ) ) # Unit tests

		session_service.set_proxy_session( session_id, session_proxy )

		# If these jobs die with an error, then they may leak the
		# TCP socket up in the handler? (That may have been send_into_ws not exiting.)

		def _do_send(message):
			session = session_service.get_session( session_id )
			if session: session.get_client_msgs() # prevent buildup
			if message is None:
				if session:
					try:
						session.kill()
					except Exception: pass
				return False
			return True
		# TODO: We need to capture this retry pattern somewhere.
		# The transaction.Attempts class is somewhat broken in 1.2.0
		# (see pyramid_tm 0.3) so we cannot use it. pyramid_tm has a replacement,
		# but it's private
		@_catch_all
		def send_into_ws():
			listen = True
			while listen:
				message = session_proxy.get_client_msg()
				for _ in range(2):
					try:
						listen = False
						with context_manager_callable():
							cont = _do_send( message )
							if not cont:
								break
						# A successful commit! Yay! Go again
						listen = True
						break
					except transaction.interfaces.TransientError:
						logger.exception( "Retrying send_into_ws on transient error" )


				if not listen:
					# Don't send a message if the transactions failed
					# and we're going to break this loop
					break
				encoded = None
				try:
					assert isinstance(message, str), "Messages should already be encoded as required"
					#encoded = component.getUtility( interfaces.ISocketIOProtocolFormatter, name='1' ).encode( message )
					websocket.send(message)
				except socket.error:
					# The session will be killed of its own accord soon enough.
					break
				#except UnicodeError:
				#	logger.exception( "Failed to send message that couldn't be encoded: '%s' => '%s'",
				#					  message, encoded )

		def _do_read(message):
			session = session_service.get_session( session_id )
			if session is None:
				return False

			if message is None:
				# Kill the greenlet
				session_proxy.put_client_msg( None )
				# and the session
				session.kill()
				return False


			try:
				_decode_packet_to_session( session, session.socket, message )
			except Exception:
				logger.exception( "Failed to read packets from WS; killing session %s", session_id )
				session.kill()
				return False

			return True

		@_catch_all
		def read_from_ws():
			listen = True
			while listen:
				message = websocket.wait()
				for _ in range(2):
					try:
						with context_manager_callable():
							cont = _do_read(message)
							if not cont:
								listen = False
								break
						break
					except transaction.interfaces.TransientError:
						logger.exception( "Retrying read_from_ws on transient error" )


		ping_sleep = kwargs.get( 'ping_sleep', 5.0 )
		@_catch_all
		def ping():
			while True:
				gevent.sleep( ping_sleep )
				# FIXME: Make time a config?
				with context_manager_callable():
					session = session_service.get_session( session_id )
					if session and session.connected:
						session.socket.send_heartbeat()
					else:
						break

		gr1 = gevent.spawn(send_into_ws)
		gr2 = gevent.spawn(read_from_ws)

		heartbeat = gevent.spawn( ping )

		# make the section appear connected
		args[0].connection_confirmed = True
		args[0].incr_hits()

		return [gr1, gr2, heartbeat]

	def kill( self ):
		self.websocket.close_connection()
