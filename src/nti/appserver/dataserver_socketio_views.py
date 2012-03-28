#!/usr/bin/env python
"""
Views to incorporate socket.io into a pyramid application.

Only XHRPolling and WebSocket transports are supported. JSONP is not supported.

"""

from __future__ import print_function, unicode_literals

import logging
logger = logging.getLogger( __name__ )

from zope import component
from zope import interface

from pyramid.view import view_config
import pyramid.security as sec
import pyramid.httpexceptions as hexc
import pyramid.interfaces

import transaction
import gevent
import pyramid_zodbconn
from Queue import Empty
from gevent.queue import Queue
import socket



import nti.dataserver.interfaces as nti_interfaces
import nti.dataserver.session_consumer
from nti.dataserver.socketio_server import Session



RT_HANDSHAKE = 'socket.io.handshake'
RT_CONNECT = 'socket.io.connect'

URL_HANDSHAKE = '/socket.io/1/'
# We could use different hard-coded urls for the connect
URL_CONNECT = '/socket.io/1/{transport}/{session_id}'

def _after_create_session( session, request ):
	username = sec.authenticated_userid( request )
	if not username:
		logger.debug( "Unauthenticated session request" )
		raise hexc.HTTPUnauthorized()
	logger.debug( "Creating session handler for '%s'", username )
	session.owner = username
	session.message_handler = nti.dataserver.session_consumer.SessionConsumer(username=username,session=session)


def _create_new_session(request):
	def factory(**kwargs):
		s = Session(**kwargs)
		_after_create_session( s, request )
		return s

	session_manager = component.getUtility( nti_interfaces.IDataserver ).session_manager
	session = session_manager.create_session( session_class=factory )
	logger.debug( "Created new session %s", session )
	return session



@view_config(route_name=RT_HANDSHAKE) # POST or GET
def _handshake_view( request ):
	"""
	The first step in socket.io. A handshake begins the process by
	requesting a new session, we send back the session id and some miscelaneous
	information.
	"""
	# TODO: Always creating a session here is a potential DOS?
	# We need to require them to be authenticated
	session = _create_new_session(request)
	#data = "%s:15:10:jsonp-polling,htmlfile" % (session.session_id,)
	# session_id:heartbeat_seconds:close_timeout:supported_type, supported_type
	data = "%s:15:10:%s" % (session.session_id, ",".join(HANDLER_TYPES.keys()))
	data = data.encode( 'ascii' )
	# We are not handling JSONP here

	response = request.response
	response.body = data
	response.content_type = 'text/plain'
	return response

from zope.component.hooks import setSite

@view_config(route_name=RT_CONNECT) # Any request method
def _connect_view( request ):
	# Users must be authenticated. All users are allowed to make connections
	# So this is a hamfisted way of achieving that policy
	if not sec.authenticated_userid( request ):
		raise hexc.HTTPUnauthorized()

	environ = request.environ
	transport = request.matchdict.get( 'transport' )
	session_id = request.matchdict.get( 'session_id' )
	if (transport == 'websocket' and 'wsgi.websocket' not in environ)\
	  or (transport != 'websocket' and 'wsgi.websocket' in environ):
	  # trying to use an upgraded websocket on something that is not websocket transport,
	  # or vice/versa
	  raise hexc.HTTPForbidden( )

	session = component.getUtility( nti_interfaces.IDataserver ).session_manager.get_session( session_id )
	if session is None:
		raise hexc.HTTPNotFound()
	if not session.owner:
		logger.warn( "Found session with no owner. Cannot connect: %s", session )
		raise hexc.HTTPForbidden()

	# If we're restoring a previous session, we
	# must switch to using the protocol from
	# it to preserve JSON vs plist and other settings
	environ['socketio'] = session.new_protocol( ) # handler=environ['socketio'].handler )

	# Make the session object available for WSGI apps
	environ['socketio'].session = session

	# Create a transport and handle the request likewise
	transport = HANDLER_TYPES[transport](request)
	request_method = environ.get("REQUEST_METHOD")
	jobs_or_response = transport.connect(session, request_method)
	# If we have connection jobs (websockets)
	# we need to stay in this call stack so that the
	# socket is held open for reading by the server
	# and that the events continue to fire for it
	# (Other things might be in that state too)
	# We have to close the connection and commit the transaction
	# if we do expect to stick around a long time
	if 'wsgi.websocket' in environ:
		# Basically, undo the things done by application._on_new_request
		# and the tweens.
		# TODO: This is weird, better cooperation (a function in the environment?)
		transaction.commit()
		pyramid_zodbconn.get_connection(request).close()
		setSite( None )
	if pyramid.interfaces.IResponse.providedBy( jobs_or_response ):
		return jobs_or_response

	if jobs_or_response:
		gevent.joinall(jobs_or_response)
	return request.response



class BaseTransport(object):
	"""Base class for all transports. Mostly wraps handler class functions."""

	def __init__(self, request):
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
		self.protocol = self.request.environ['socketio']

	# FIXME: These encode/decode things don't really belong hanging off
	# of here, especially not off of the object that came out of the initial
	# request (since it will be changing over time in the websocket case)
	# FIXME: The send() method of SocketIOProtocol is broken, it relies
	# on being able to find sessions in the wrong place...but I don't think
	# we use that at all

	def encode(self, data):
		return self.protocol.encode(data)

	def decode(self, data):
		return self.protocol.decode(data)

	def decode_multi( self, data ):
		return self.protocol.decode_multi( data )



class XHRPollingTransport(BaseTransport):
	def __init__(self, *args, **kwargs):
		super(XHRPollingTransport, self).__init__(*args, **kwargs)

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


	def connect(self, session, request_method ):
		if not session.connection_confirmed:
			# This is either the first time in,
			# or we've had an error. If it was an
			# error, then this could either be a POST
			# or a GET. We can handle GETs the same,
			# POSTs may have data (depending on if the
			# client thinks it should re-connect) that
			# need to be dealt with...
			session.connection_confirmed = True
			if request_method == 'POST' and self.request.content_length:
				self.post( session, response_message="1::" )
			else:
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

	def __init__( self, *args ):
		super(WebsocketTransport,self).__init__(*args)
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

		@_catch_all
		def send_into_ws():
			while True:
				message = session_proxy.get_client_msg()
				with context_manager_callable():
					session = session_service.get_session( session_id )
					if session: session.get_client_msgs() # prevent buildup
					if message is None:
						if session:
							try:
								session.kill()
							except Exception: pass
						break
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

		@_catch_all
		def read_from_ws():
			while True:
				message = websocket.wait()
				with context_manager_callable():
					session = session_service.get_session( session_id )
					if session is None:
						break

					if message is None:
						# Kill the greenlet
						session_proxy.put_client_msg( None )
						# and the session
						session.kill()
						break

					decoded_message = None
					try:
						decoded_message = self.decode(message)
					except Exception:
						decoded_message = None
						session.kill()
						break

					if decoded_message is not None:
						session.put_server_msg(decoded_message)

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
HANDLER_TYPES = {
	'websocket': WebsocketTransport,
	'xhr-polling': XHRPollingTransport
	}
