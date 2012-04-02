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
import warnings

import pyramid.interfaces
from nti.socketio import interfaces
import nti.dataserver.interfaces as nti_interfaces

#import nti.dataserver.session_consumer
#from nti.dataserver.socketio_server import Session


#import nti.dataserver.sessions as _sessions
#import nti.dataserver.datastructures as datastructures
#import json
import nti.socketio.protocol

class BaseTransport(object):
	"""Base class for all transports. Mostly wraps handler class functions."""

	def __init__(self, request):
		"""
		:param request: A :class:`pyramid.request.Request` object.
		"""
		self.content_type = ("Content-Type", "text/plain; charset=UTF-8")
		self.headers = [
			("Access-Control-Allow-Origin", "*"),
			("Access-Control-Allow-Credentials", "true"),
			("Access-Control-Allow-Methods", "POST, GET, OPTIONS"),
			("Access-Control-Max-Age", 3600),
		]
		self.headers_list = []
		self.handler = request
		self.request = request
		#self.protocol = self.request.environ['socketio']

	# FIXME: These encode/decode things don't really belong hanging off
	# of here, especially not off of the object that came out of the initial
	# request (since it will be changing over time in the websocket case)
	# FIXME: The send() method of SocketIOProtocol is broken, it relies
	# on being able to find sessions in the wrong place...but I don't think
	# we use that at all

	@property
	def protocol(self):
		return self.request.environ['socketio']

	def encode(self, data):
		return self.protocol.encode(data)

	def decode(self, data):
		return self.protocol.decode(data)

	def decode_multi( self, data ):
		return self.protocol.decode_multi( data )

	def kill(self):
		pass



class XHRPollingTransport(BaseTransport):
	component.adapts( pyramid.interfaces.IRequest )
	interface.implements( interfaces.ISocketIOTransport )

	def __init__(self, request):
		super(XHRPollingTransport, self).__init__(request)

	def write(self, data=""):
		# In gevent 0.x, pywsgi established response_headers and response_headers_list
		# as soon as start_response was finished, and socketio relied on this.
		# In gevent 1.0, this no longer happens because final headers are deferred until finalize_headers()
		# is called, which is the first time data is written.
		# Thus, we do it ourself
		if not hasattr( self.handler, 'response_headers_list'):
			warnings.warn( "Applying compatibility shim for gevent/socketio response_headers_list" )
			self.handler.response_headers_list = [x[0] for x in self.handler.response_headers]
		super(XHRPollingTransport,self).write( data=data )

	def options(self):
		rsp = self.request.response
		rsp.content_type = 'text/plain'
		return rsp


	def get(self, session):
		session.clear_disconnect_timeout()
		session_proxy = _SessionEventProxy()
		session_service = component.getUtility( nti_interfaces.IDataserver ).session_manager
		session_service.set_proxy_session( session.session_id, session_proxy )
		try:
			# A dead session will feed us a None object
			# whereupon...we blow up...
			messages = session.get_client_msgs()
			if not messages:
				# Nothing to read right now.
				# The client expects us to block, though, for some time
				# We use our session proxy to both wait
				# and notify us immediately if a new message comes in
				# Note that if we get a message via broadcast,
				# our cached session is going to be behind, so it's
				# pointless to try to read from it again. Unfortunately,
				# to avoid duplicate messages, we cannot just send
				# this one to the client (since its still in the session).
				# The simplest thing to do is to immediately return
				# and let the next poll pick up the message.
				# TODO: It may be possible to back out of the transaction
				# and retry.
				session_proxy.get_client_msg( timeout=5.0 )
				if messages == None or not messages:
					raise Empty()
			message = messages[0]
			message = self.encode(message)
			# Are there any more we can get immediately? If so, do it
			# and add them on. This will raise Empty and we'll break
			# out of the loop.
			if messages[1:]:
				# The first one is a little special.
				m2 = messages[1]
				m2 = self.encode( m2 )
				def wrap( msg ):
					return '\xef\xbf\xbd' + str( len( msg ) ) + '\xef\xbf\xbd' + msg

				message = wrap( message ) + wrap( m2 )

				for m2 in messages[2:]:
					m2 = self.encode( m2 )
					message = message + wrap( m2 )
		except (Empty,IndexError):
			message = "8::" # NOOP

		response = self.request.response
		response.body = message.encode( 'utf-8' )
		return response

	def _request_body(self):
		return self.request.body


	def post(self, session, response_message="8::"):
		try:
			pckts = self.decode_multi( self._request_body() )
			for pckt in pckts:
				if pckt is not None:
					session.put_server_msg( pckt )
		except Exception:
			logger.exception( "Failed te get post in XHRPolling; unconfirming connection" )
			# The client will expect to re-confirm the session
			# by sending a blank post when it gets an error.
			# Our state must match.
			session.connection_confirmed = False
			raise

		response = self.request.response
		response.content_type = 'text/plain'
		response.headers['Connection'] = 'close'
		response.body = response_message.encode( 'utf-8' )
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
				response = self.post( session, response_message="1::" )
			else:
				response = self.request.response
				response.headers['Connection'] = 'close'
				response.body =  b"1::"

			return response

		if request_method == 'POST' and not self.request.content_length:
			# We have a session that WAS confirmed, but the client
			# thinks it is no longer confirmed...we're probably switching transports
			# due to a hard crash of an instance. So treat this
			# like a fresh connection
			response = self.request.response
			response.headers['Connection'] = 'close'
			response.body =  b"1::"
			return response

		if request_method in ("GET", "POST", "OPTIONS"):
			try:
				return getattr(self, request_method.lower())(session)
			except ValueError:
				# TODO: What if its binary data?
				logger.debug( "Failed to parse incoming body '%s'", self._request_body(), exc_info=True )
				raise

		raise Exception("No support for the method: " + request_method)


# import wsgiref.headers

# def _add_cors_headers( headers, environ ):
# 	# TODO: This is copied from appserver.cors
# 	theHeaders = wsgiref.headers.Headers( headers )
# 	# For simple requests, we only need to set
# 	# -Allow-Origin, -Allow-Credentials, and -Expose-Headers.
# 	# If we fail, we destroy the browser's cache.
# 	# Since we support credentials, we cannot use the * wildcard origin.
# 	theHeaders['Access-Control-Allow-Origin'] = environ['HTTP_ORIGIN']
# 	theHeaders['Access-Control-Allow-Credentials'] = "true" # case-sensitive

# 	# We would need to add Access-Control-Expose-Headers to
# 	# expose non-simple response headers to the client, even on simple requests

# 	# All the other values are only needed for preflight requests,
# 	# which are OPTIONS
# 	if environ['REQUEST_METHOD'] == 'OPTIONS':
# 		theHeaders['Access-Control-Allow-Methods'] = 'POST, GET, PUT, DELETE, OPTIONS'
# 		theHeaders['Access-Control-Max-Age'] = "1728000" # 20 days
# 		theHeaders['Access-Control-Allow-Headers'] = 'X-Requested-With, Authorization, If-Modified-Since, Content-Type, Origin, Accept, Cookie'

# import geventwebsocket.handler
# class WebSocketHandler(geventwebsocket.handler.WebSocketHandler):
# 	"""
# 	Because the websocket handles its own header responses,
# 	we must make it output CORS info. Once we get here,
# 	we know we will never call the user's app.
# 	"""

# 	def start_response(self, status, headers, exc_info=None):
# 		if 'HTTP_ORIGIN' in self.environ:
# 			_add_cors_headers( headers, self.environ )
# 		super(WebSocketHandler,self).start_response( status, headers, exc_info )


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

		websocket = self.handler.environ['wsgi.websocket']
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
														   default=getattr( self.handler, 'context_manager_callable', None ) ) # Unit tests

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
						with context_manager_callable():
							cont = _do_send( message )
							if not cont:
								listen = False
								break
						break
					except transaction.interfaces.TransientError:
						logger.exception( "Retrying send_into_ws on transient error" )

				encoded = None
				try:
					encoded = self.encode( message )
					websocket.send(encoded)
				except socket.error:
					# The session will be killed of its own accord soon enough.
					break
				except UnicodeError:
					logger.exception( "Failed to send message that couldn't be encoded: '%s' => '%s'",
									  message, encoded )

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


			decoded_message = None
			try:
				decoded_message = self.decode(message)
			except Exception:
				decoded_message = None
				session.kill()
				return False

			if decoded_message is not None:
				session.put_server_msg(decoded_message)
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
						session.new_protocol( self.handler ).send_heartbeat()
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
