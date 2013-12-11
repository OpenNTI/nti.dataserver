#!/usr/bin/env python
"""
Views to incorporate socket.io into a pyramid application.

Only XHRPolling and WebSocket transports are supported. JSONP is not supported.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import transaction

from zope import component
from zope import interface
from zope.deprecation import deprecate

import pyramid.interfaces
from pyramid.view import view_config
import pyramid.httpexceptions as hexc

try:
	import gevent
except ImportError:
	gevent = None
from geventwebsocket import interfaces as ws_interfaces

from nti.appserver.policies import site_policies

import nti.dataserver.interfaces as nti_interfaces

import nti.socketio.interfaces
import nti.socketio.session_consumer
from nti.socketio.persistent_session import AbstractSession

class Session( AbstractSession ):
	"""
	Client session which checks the connection health and the queues for
	message passing.
	`self.owner`: An attribute for the user that owns the session.

	.. py:attribute:: originating_site_names

		The list of sites that apply to the request that created this session. Useful
		for applying site policies later on after the requests are gone.
	"""

	#originating_site_names = () # actually in the superclass for conflict resolution

	wsgi_app_greenlet = True # TODO: Needed anymore?

	@deprecate("Prefer the `socket` property")
	def new_protocol( self, handler=None ):
		return self.socket

	@property
	@deprecate( "Prefer the `socket` property" )
	def protocol_handler(self):
		return self.socket

	@property
	def message_handler(self):
		return nti.socketio.session_consumer.SessionConsumer()

	# TODO: We want to ensure queue behaviour for
	# server messages across the cluster. Either that, or make the interaction
	# stateless
	def queue_message_from_client(self, msg):
		# Putting a server message immediately processes it,
		# wherever the session is loaded.
		self.message_handler( self, msg )

	def queue_message_to_client(self, msg):
		session_service = component.getUtility( nti_interfaces.IDataserver ).session_manager
		session_service.queue_message_to_client( self.session_id, msg )

	def get_messages_to_client(self):
		"""
		Returns an iterable of messages to the client, or possibly None if the session is dead. These messages
		are now considered consumed and cannot be retrieved by this method again.
		"""
		session_service = component.getUtility( nti_interfaces.IDataserver ).session_manager
		return session_service.get_messages_to_client( self.session_id )

	def clear_disconnect_timeout(self):
		session_service = component.getUtility( nti_interfaces.IDataserver ).session_manager
		session_service.clear_disconnect_timeout( self.session_id )

	@property
	def last_heartbeat_time(self):
		session_service = component.getUtility( nti_interfaces.IDataserver ).session_manager
		return session_service.get_last_heartbeat_time( self.session_id, self )

	def kill( self, send_event=True ):
		self.message_handler.kill(self)
		super(Session,self).kill(send_event=send_event)

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


def _create_new_session(request):
	"""
	Creates a session for the authenticated user of the request.
	"""

	username = request.authenticated_userid
	if not username:
		logger.debug( "Unauthenticated session request" )
		raise hexc.HTTPUnauthorized()
	#gevent.sleep( 0.1 ) # Trivial throttling
	logger.debug( "Creating session handler for '%s'", username )

	session_manager = component.getUtility( nti_interfaces.IDataserver ).session_manager
	session = session_manager.create_session( session_class=Session, owner=username )
	session.originating_site_names = site_policies.get_possible_site_names( request, include_default=True )
	logger.debug( "Created new session %s with site policies %s", session, session.originating_site_names )
	return session

KNOWN_TRANSPORTS = {'websocket':1, 'flashsocket':2, 'xhr-polling':3, 'jsonp-polling':4}

@view_config(route_name=RT_HANDSHAKE) # POST or GET
def _handshake_view( request ):
	"""
	The first step in socket.io. A handshake begins the process by
	requesting a new session, we send back the session id and some miscellaneous
	information.
	"""
	session = _create_new_session(request)

	# data = "%s:15:10:jsonp-polling,htmlfile" % (session.session_id,)
	# session_id:heartbeat_seconds:close_timeout:supported_type, supported_type,...
	handler_types = [x[0] for x in component.getAdapters( (request,), nti.socketio.interfaces.ISocketIOTransport)]
	handler_types = sorted(handler_types, key=lambda x: KNOWN_TRANSPORTS.get(x, -1))
	data = "%s:15:10:%s" % (session.session_id, ",".join(handler_types))
	data = data.encode( 'ascii' )
	# NOTE: We are not handling JSONP here. It should not be a registered transport

	response = request.response
	response.body = data
	response.content_type = b'text/plain'
	return response

@interface.implementer( ws_interfaces.IWSWillUpgradeVeto )
class _WSWillUpgradeVeto(object):
	"""
	A veto handler to avoid upgrading to websockets if the session doesn't
	exist. This lets our 404 propagate.
	"""

	def __init__( self, evt=None ):
		return

	def can_upgrade( self, wswill_upgrade_event ):
		"""
		If the session exists and is valid, we can upgrade.
		"""
		# Pull the session id out of the path. See
		# URL_CONNECT
		environ = wswill_upgrade_event.environ
		sid = environ['PATH_INFO'].split( '/' )[-1]
		def test():
			try:
				_get_session( sid ) # TODO: This causes a write to the session. Why?
			except hexc.HTTPNotFound:
				logger.debug( "Not upgrading, no session", exc_info=True )
				return False
			else:
				return True
		# NOTE: Not running this in any site policies
		return component.getUtility( nti_interfaces.IDataserverTransactionRunner )( test, retries=3, sleep=0.1 )

def _get_session(session_id):
	"""
	Returns a valid session to use, or raises HTTPNotFound.
	"""
	try:
		session = component.getUtility( nti_interfaces.IDataserver ).session_manager.get_session( session_id )
	except (KeyError,ValueError):
		logger.warn( "Client sent bad value for session (%s); DDoS attempt?", session_id, exc_info=True )
		raise hexc.HTTPNotFound( "No session found or illegal session id" )

	if session is None:
		raise hexc.HTTPNotFound("No session found for %s" % session_id)
	if not session.owner:
		logger.warn( "Found session with no owner. Cannot connect: %s", session )
		raise hexc.HTTPNotFound("Session has no owner %s" % session_id )
	return session

@view_config(route_name=RT_CONNECT) # Any request method
def _connect_view( request ):

	environ = request.environ
	transport = request.matchdict.get( 'transport' )
	ws_transports = ('websocket','flashsocket')
	session_id = request.matchdict.get( 'session_id' )

	# All our errors need to come back as 404 (not 403) otherwise the browser
	# keeps trying to reconnect this same session
	if (transport in ws_transports and 'wsgi.websocket' not in environ)\
		or (transport not in ws_transports and 'wsgi.websocket' in environ):
		# trying to use an upgraded websocket on something that is not websocket transport,
		# or vice/versa
		raise hexc.HTTPNotFound( 'Incorrect use of websockets' )

	session = _get_session(session_id)

	# Users must be authenticated. All users are allowed to make connections
	# So this is a hamfisted way of achieving that policy.
	# NOTE: It seems that the 'flashsocket' transport does not actually set
	# up authentication
	if not request.authenticated_userid:
		if transport == 'flashsocket':
			logger.warn( "Allowing unauthenticated flashsocket use from %s", request )
		else:
			raise hexc.HTTPUnauthorized()


	# Make the session object available for WSGI apps
	environ['socketio'] = session.socket
	environ['socketio'].session = session # TODO: Needed anymore?

	# Create a transport and handle the request likewise
	try:
		transport = component.getAdapter( request, nti.socketio.interfaces.ISocketIOTransport, name=transport )
	except LookupError:
		raise hexc.HTTPNotFound( "Unknown transport type %s" % transport )

	request_method = environ.get("REQUEST_METHOD")
	try:
		jobs_or_response = transport.connect(session, request_method)
	except IOError:
		logger.debug( "Client disconnected during connection", exc_info=True )
		raise hexc.HTTPClientError()

	if pyramid.interfaces.IResponse.providedBy( jobs_or_response ):
		return jobs_or_response

	# If we have connection jobs (websockets)
	# we need to stay in this call stack so that the
	# socket is held open for reading by the server
	# and that the events continue to fire for it
	# (Other things might be in that state too)
	# We have to close the connection and commit the transaction
	# if we do expect to stick around a long time
	# TODO: If this process raises and we wind up hitting the retry logic,
	# how does this react?
	if 'wsgi.websocket' in environ:
		# See application.py
		try:
			environ['nti.early_request_teardown'](request)
		except Exception: # Most commonly a ConflictError or commit
			# Gotta kill the jobs
			exc_info = sys.exc_info()
			logger.exception( "Failed to teardown request; aborting" )
			try:
				transaction.doom() # No use trying again
			except ValueError:
				# If the exception was raised while we were actually
				# committing the transaction, then we won't be able to doom it,
				# it's too late.
				pass
			transport.kill()
			for job in jobs_or_response:
				job.kill()
			# Re-raise the original, not the ValueError that probably fired
			raise exc_info[0], None, exc_info[2]


	if jobs_or_response:
		gevent.joinall(jobs_or_response)
	return request.response
