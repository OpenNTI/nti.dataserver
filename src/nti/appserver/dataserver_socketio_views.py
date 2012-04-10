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
from zope.deprecation import deprecate

from pyramid.view import view_config
import pyramid.security as sec
import pyramid.httpexceptions as hexc
import pyramid.interfaces

import transaction
import gevent
import pyramid_zodbconn


import nti.socketio.interfaces
import nti.dataserver.interfaces as nti_interfaces
import nti.dataserver.session_consumer
#from nti.dataserver.socketio_server import Session


import nti.dataserver.sessions as _sessions
import nti.dataserver.datastructures as datastructures
import json

from nti.socketio import interfaces as socketio_interfaces
import nti.socketio.protocol

class Session( _sessions.Session ):
	"""
	Client session which checks the connection health and the queues for
	message passing.
	`self.owner`: An attribute for the user that owns the session.
	"""

	interface.implements( socketio_interfaces.ISocketIOChannel )

	def __init__(self,**kwargs):
		super(Session,self).__init__(**kwargs)
		self.wsgi_app_greenlet = True
		self.message_handler = None

	@deprecate("Prefer the `socket` property")
	def new_protocol( self, handler=None ):
		return self.socket

	@property
	@deprecate( "Prefer the `socket` property" )
	def protocol_handler(self):
		return self.socket

	@property
	def socket(self):
		p = nti.socketio.protocol.SocketIOSocket( self )
		#p.session = self
		return p


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
			self.message_handler( self.socket, msg )

	def put_client_msg(self, msg):
		self.session_service.put_client_msg( self.session_id, msg )

	def get_client_msgs(self):
		return self.session_service.get_client_msgs( self.session_id )

	def kill( self ):
		if hasattr( self.message_handler, 'kill' ):
			self.message_handler.kill()
		super(Session,self).kill()

# b/c
import sys
import UserDict
socketio_server = UserDict.UserDict()
socketio_server['Session'] = Session
socketio_server.Session = Session
sys.modules['nti.dataserver.socketio_server'] = socketio_server
nti.dataserver.socketio_server = socketio_server


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
	handler_types = [x[0] for x in component.getAdapters( (request,), nti.socketio.interfaces.ISocketIOTransport)]
	data = "%s:15:10:%s" % (session.session_id, ",".join(handler_types))
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
	ws_transports = ('websocket','flashsocket')
	session_id = request.matchdict.get( 'session_id' )

	if (transport in ws_transports and 'wsgi.websocket' not in environ)\
	  or (transport not in ws_transports and 'wsgi.websocket' in environ):
	  # trying to use an upgraded websocket on something that is not websocket transport,
	  # or vice/versa
	  raise hexc.HTTPForbidden( 'Incorrect use of websockets' )

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
	transport = component.getAdapter( request, nti.socketio.interfaces.ISocketIOTransport, name=transport )
	request_method = environ.get("REQUEST_METHOD")
	jobs_or_response = transport.connect(session, request_method)

	if pyramid.interfaces.IResponse.providedBy( jobs_or_response ):
		return jobs_or_response

	# If we have connection jobs (websockets)
	# we need to stay in this call stack so that the
	# socket is held open for reading by the server
	# and that the events continue to fire for it
	# (Other things might be in that state too)
	# We have to close the connection and commit the transaction
	# if we do expect to stick around a long time
	if 'wsgi.websocket' in environ:
		# See application.py
		environ['nti.early_request_teardown'](request)


	if jobs_or_response:
		gevent.joinall(jobs_or_response)
	return request.response
