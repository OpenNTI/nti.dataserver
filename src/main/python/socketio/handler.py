import sys
import re
import gevent
import urlparse
import traceback
import time

import gevent.pywsgi as pywsgi
from socketio import transports
import geventwebsocket
from geventwebsocket.handler import WebSocketHandler


class SocketIOHandler(pywsgi.WSGIHandler):
	RE_REQUEST_URL = re.compile(r"""
		^/(?P<namespace>[^/]+)
		 /(?P<protocol_version>1)
		 /(?P<transport_id>[^/]+)
		 /(?P<session_id>[^/]+)/?$
		 """, re.X)
	RE_HANDSHAKE_URL = re.compile(r"^/(?P<namespace>[^/]+)/1/$", re.X)

	handler_types = {
		'websocket': transports.WebsocketTransport,
		'flashsocket': transports.FlashSocketTransport,
		'htmlfile': transports.HTMLFileTransport,
		'xhr-multipart': transports.XHRMultipartTransport,
		'xhr-polling': transports.XHRPollingTransport,
		'jsonp-polling': transports.JSONPolling,
	}

	def __init__(self, socket, address, server, rfile=None, sessions=None):

		"""
		:param sessions: The location for session data. Has `get_session` and
			`create_new_session` methods.
		"""

		super(SocketIOHandler, self).__init__(socket, address, server, rfile=rfile)
		if sessions is None:
			raise ValueError( "Sessions cannot be None" )
		self._sessions = sessions

	def write_jsonp_result(self, data, wrapper="0"):
		self.start_response("200 OK", [
			("Content-Type", "application/javascript"),
		])
		self.result = ['io.j[%s]("%s");' % (wrapper, data)]

	def write_plain_result(self, data):
		self.start_response("200 OK", [
			("Content-Type", "text/plain")
		])
		self.result = [data]

	def write_smart(self, data):
		args = urlparse.parse_qs(self.environ.get("QUERY_STRING"))

		if "jsonp" in args:
			self.write_jsonp_result(data, args["jsonp"][0])
		else:
			self.write_plain_result(data)

		self.process_result()

	def handle_one_response(self, **kwargs):
		"""
		Deals with responding to one request. Either calls the application,
		or :meth:`do_handle_one_socketio_response` for SocketIO.
		"""
		self.status = None
		self.headers_sent = False
		self.result = None
		self.response_length = 0
		self.response_use_chunked = False

		path = self.environ.get('PATH_INFO')

		request_tokens = self.RE_REQUEST_URL.match(path)
		handshake_tokens = self.RE_HANDSHAKE_URL.match(path)

		# Parse request URL and QUERY_STRING and do handshake, if appropriate
		if not request_tokens and not handshake_tokens:
			# Neither an ongoing (poll) request nor initial handshake.
			# over to the app
			return super(SocketIOHandler,self).handle_one_response()

		return self.do_handle_one_socketio_response( request_tokens, handshake_tokens )

	def do_handle_one_socketio_response( self, request_tokens, handshake_tokens ):
		"""
		Called to handle SocketIO related handshake and communication.
		"""
		if handshake_tokens:
			# initial handshake, yay
			return self._do_handle_socketio_handshake_response( handshake_tokens.groupdict() )

		# Ongoing request, including websocket upgrades. Sweet.
		request_tokens = request_tokens.groupdict()
		return self.do_handle_one_socketio_session_response( request_tokens )

	def _do_handle_socketio_handshake_response(self, tokens):
		if tokens["namespace"] != self.server.namespace:
			self.log_error("Namespace mismatch")
		else:
			session = self._sessions.create_new_session()
			#data = "%s:15:10:jsonp-polling,htmlfile" % (session.session_id,)
			data = "%s:15:10:%s" % (session.session_id, ",".join(self.handler_types.keys()))
			self.write_smart(data)

	def do_handle_one_socketio_session_response( self, request_tokens ):
		"""
		Called to handle SocketIO communication, after a handshake and session
		have been established.
		"""

		# Setup the transport and session
		transport_class = self.handler_types.get(request_tokens["transport_id"])
		session_id = request_tokens["session_id"]

		# In case this is WebSocket request, switch to the WebSocketHandler
		# FIXME: fix this ugly class change
		try:
			session = self._sessions.get_session(session_id)
			# If we're restoring a previous session, we
			# must switch to using the protocol from
			# it to preserve JSON vs plist and other settings
			self.environ['socketio'] = session.new_protocol( handler=self.environ['socketio'].handler )

			if issubclass( transport_class, (transports.WebsocketTransport,
											 transports.FlashSocketTransport)):
				self.__class__ = WebSocketHandler
				self.handle_one_response(call_wsgi_app=False)

			# Make the session object available for WSGI apps
			self.environ['socketio'].session = session

			# Create a transport and handle the request likewise
			transport = transport_class(self)
			request_method = self.environ.get("REQUEST_METHOD")
			jobs = transport.connect(session, request_method)
			try:
				if not session.wsgi_app_greenlet or not bool(session.wsgi_app_greenlet):
					session.wsgi_app_greenlet = gevent.spawn(self.application, self.environ, lambda status, headers, exc=None: None)
			except Exception:
				traceback.print_exc()
				# our transports connect method may have already written
				# headers and body.
				if not self.response_length:
					self.start_response(pywsgi._INTERNAL_ERROR_STATUS, pywsgi._INTERNAL_ERROR_HEADERS, sys.exc_info())
					self.write(pywsgi._INTERNAL_ERROR_BODY)

			# If we have connection jobs (websockets)
			# we need to stay in this call stack so that the
			# socket is held open for reading by the server
			# and that the events continue to fire for it
			gevent.joinall(jobs)
		finally:
			self.time_finish = time.time()
			self.log_request()
