""" Socket IO server and sessions that work with the dataserver. """
import logging
logger = logging.getLogger( __name__ )

import traceback

from Queue import Empty
from gevent.queue import Queue
import gevent

import socket
import socketio
import geventwebsocket.handler
import wsgiref

#anyjson uses lambda functions that cannot be pickled
#import anyjson as json
import json
import transaction

from zope import component
from nti.dataserver import interfaces as nti_interfaces

__all__ = ['SocketIOServer', 'Session']

class SocketIOServer(socketio.SocketIOServer):
	"""A WSGI Server with a resource that acts like an SocketIO."""

	def __init__(self, *args, **kwargs):
		"""
		If the `handler_class` does not refer to a :class:`SocketIOHandler`, it
		will be forced to do so.

		:param handler_kwargs: A dictionary of arguments to pass to the SocketIOHandler.
		:param session_manager: A :class:`nti.dataserver.sessions.SessionService`.
		"""
		self.session_manager = kwargs.pop( 'session_manager' )
		handler_kwargs = kwargs.pop( 'handler_kwargs', None ) or {}
		super(SocketIOServer,self).__init__( *args, **kwargs )
		self.handler_kwargs = handler_kwargs
		if not issubclass( getattr( self, 'handler_class', None ), SocketIOHandler ):
			self.handler_class = SocketIOHandler

	def handle(self, sock, address):
		handler = self.handler_class(sock, address, self,
									 sessions=self,
									 context_manager_callable=component.getUtility(nti_interfaces.IDataserver).dbTrans,
									 **self.handler_kwargs)
		self.set_environ({'socketio': socketio.protocol.SocketIOProtocol(handler)})
		handler.handle()

	# Sessions
	## TODO: I don't really care for these being here. Factor
	## them into their own class.

	def create_new_session( self ):
		""" Creates a new session. Upon return, it will be visible to all connections. """
		session = None
		session = self.session_manager.create_session( session_class=Session )
		self._after_create_session( session )
		logger.debug( "Created new session %s", session )
		return session

	def get_session(self, session_id=None):
		"""
		:return: an existing client Session.
		:raises KeyError: If the session asked for does not exist.
		"""
		session = self.session_manager.get_session( session_id )
		if not session:
			raise KeyError( "No session " + str(session_id) )
		return session

	# def kill_session( self, session ):
	#	"""Kills an existing session or session id. Removes it from the store."""
	#	if hasattr( session, 'session_id' ):
	#		self.kill_session( session.session_id )
	#	elif session:
	#		try:
	#			self.sessions.delete_session( session )
	#		except KeyError: pass

	def _after_create_session( self, session ):
		pass

def _add_cors_headers( headers, environ ):
	# TODO: This is copied from appserver.cors
	theHeaders = wsgiref.headers.Headers( headers )
	# For simple requests, we only need to set
	# -Allow-Origin, -Allow-Credentials, and -Expose-Headers.
	# If we fail, we destroy the browser's cache.
	# Since we support credentials, we cannot use the * wildcard origin.
	theHeaders['Access-Control-Allow-Origin'] = environ['HTTP_ORIGIN']
	theHeaders['Access-Control-Allow-Credentials'] = "true" # case-sensitive

	# We would need to add Access-Control-Expose-Headers to
	# expose non-simple response headers to the client, even on simple requests

	# All the other values are only needed for preflight requests,
	# which are OPTIONS
	if environ['REQUEST_METHOD'] == 'OPTIONS':
		theHeaders['Access-Control-Allow-Methods'] = 'POST, GET, PUT, DELETE, OPTIONS'
		theHeaders['Access-Control-Max-Age'] = "1728000" # 20 days
		theHeaders['Access-Control-Allow-Headers'] = 'X-Requested-With, Authorization, If-Modified-Since, Content-Type, Origin, Accept, Cookie'

class WebSocketHandler(geventwebsocket.handler.WebSocketHandler):
	"""
	Because the websocket handles its own header responses,
	we must make it output CORS info. Once we get here,
	we know we will never call the user's app.
	"""

	def start_response(self, status, headers, exc_info=None):
		if 'HTTP_ORIGIN' in self.environ:
			_add_cors_headers( headers, self.environ )
		super(WebSocketHandler,self).start_response( status, headers, exc_info )


class SocketIOHandler(socketio.handler.SocketIOHandler):

	_add_cors_ = False

	def __init__( self, *args, **kwargs ):
		"""
		:param socket socket: The client socket.
		:param tuple address: Indexable object. First item is client IP string.
		:param server: A WSGIServer. Has `application` property and `get_environ` method.
		:param rfile: Optional file-like object to read from.
		:param callable context_manager_callable: A callable that produces a context manager which
			will be wrapped around each handled client request.
		"""
		self.context_manager_callable = kwargs.pop( 'context_manager_callable' )
		self.handling_session_cm = None
		super(SocketIOHandler, self).__init__( *args, **kwargs )
		self.handler_types = {
			'websocket': WebsocketTransport,
			'xhr-polling': XHRPollingTransport
		}
		self.websocket_connection = False # Because the super swizzles classes
		self.web_socket_handler = WebSocketHandler

	def handle_one_response( self, *args, **kwargs ):
		self.handling_session_cm = self.context_manager_callable()
		# TODO: We should wrap this with error handling and do something
		# on conflict errors and the like.
		try:
			try:
				with self.handling_session_cm as conn:
					self.environ['app.db.connection'] = conn
					super(SocketIOHandler,self).handle_one_response( *args, **kwargs )
			except transaction.interfaces.TransientError:
				logger.exception( "Error handling socket.io response" )
				if callable( getattr( self, 'reset_passenger', None ) ):
					getattr( self, 'reset_passenger' )()
				self.start_response( '201 Not Modified', [] )
		except :
			logger.exception( "Error handling one response" )
			if callable( getattr( self, 'reset_passenger', None ) ):
				getattr( self, 'reset_passenger' )()
			self.start_response( '201 Not Modified', [] )

	def start_response(self, status, headers, exc_info=None):
		if self._add_cors_ and 'HTTP_ORIGIN' in self.environ:
			_add_cors_headers( headers, self.environ )
		super(SocketIOHandler,self).start_response( status, headers, exc_info )

	def do_handle_one_socketio_response( self, *args ):
		self._add_cors_ = True
		super(SocketIOHandler,self).do_handle_one_socketio_response( *args )


import sessions as _sessions
import datastructures

class Session( _sessions.Session ):
	"""
	Client session which checks the connection health and the queues for
	message passing.
	`self.owner`: An attribute for the user that owns the session.
	"""

	def __init__(self):
		super(Session,self).__init__()
		self.wsgi_app_greenlet = True
		self.message_handler = None
		self.externalize_function = datastructures.to_json_representation
		self.internalize_function = json.loads


	def new_protocol( self, handler=None ):
		p = socketio.protocol.SocketIOProtocol( handler )
		p.session = self
		return p

	protocol_handler = property(new_protocol)

	# The names are odd. put_server_msg is a message TO
	# the server. That is, a message arriving at the server,
	# sent from the client. In contrast, put_client_msg
	# is a message to send TO the client, FROM the server.

	# TODO: We want to ensure queue behaviour for
	# server messages across the cluster. Either that, or make the interaction
	# stateless
	def put_server_msg(self, msg):
		# Putting a server message immediately processes it,
		# wherever the session is loaded.
		if callable(self.message_handler):
			with self.session_service.session_db_cm():
				self.message_handler( self.protocol_handler, msg )

	def put_client_msg(self, msg):
		self.session_service.put_client_msg( self.session_id, msg )

	def get_client_msgs(self):
		return self.session_service.get_client_msgs( self.session_id )

	def kill( self ):
		if hasattr( self.message_handler, 'kill' ):
			self.message_handler.kill()
		super(Session,self).kill()


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

class XHRPollingTransport(socketio.transports.XHRPollingTransport):
	def __init__(self, *args, **kwargs):
		super(XHRPollingTransport, self).__init__(*args, **kwargs)

	def get(self, session):
		session.clear_disconnect_timeout()
		session_proxy = _SessionEventProxy()
		session_service = self.handler.server.session_manager
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

		self.start_response("200 OK", [])
		self.write(message)

		return []

	def post(self, session, response_message="8::"):
		try:
			pckts = self.decode_multi( self._request_body() )
			for pckt in pckts:
				if pckt is not None:
					session.put_server_msg( pckt )
		except Exception:
			traceback.print_exc()
			# The client will expect to re-confirm the session
			# by sending a blank post when it gets an error.
			# Our state must match.
			session.connection_confirmed = False
			raise

		self.start_response("200 OK", [
			("Connection", "close"),
			("Content-Type", "text/plain")
		])
		self.write(response_message)

		return []

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
			if request_method == 'POST' and self.handler.environ['CONTENT_LENGTH'] != '0':
				self.post( session, response_message="1::" )
			else:
				self.start_response("200 OK", [
					("Connection", "close"),
					])
				self.write("1::")

			return []

		if request_method in ("GET", "POST", "OPTIONS"):
			return getattr(self, request_method.lower())(session)

		raise Exception("No support for the method: " + request_method)


class JSONPolling(XHRPollingTransport):
	pass

class WebsocketTransport(socketio.transports.WebsocketTransport):

	def __init__( self, *args ):
		super(WebsocketTransport,self).__init__(*args)
		self.websocket = None

	def connect(self, *args):

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
		session_service = self.handler.server.session_manager
		context_manager_callable = self.handler.context_manager_callable
		session_service.set_proxy_session( session_id, session_proxy )


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

		def read_from_ws():
			while True:
				message = websocket.wait()
				with context_manager_callable():
					session = session_service.get_session( session_id )
					if session is None:
						break

					if message is None:
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

		def ping():
			while True:
				gevent.sleep( 5.0 )
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
		# Stop making changes to the session, and close
		# the connection. We'll never return from this.
		self.handler.handling_session_cm.premature_exit_but_its_okay()
		return [gr1, gr2, heartbeat]

	def kill( self ):
		self.websocket.close_connection()
