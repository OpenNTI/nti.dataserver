#!/usr/bin/env python
"""
Views to incorporate socket.io into a pyramid application.

Only XHRPolling and WebSocket transports are supported. JSONP is not supported.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from . import MessageFactory as _

import sys
import UserDict

import transaction

from zope import component
from zope import interface

from pyramid.view import view_config
from pyramid.interfaces import IResponse
from pyramid import httpexceptions as hexc

from geventwebsocket.interfaces import IWSWillUpgradeVeto

from nti.appserver.policies import site_policies

from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IDataserverTransactionRunner

import nti.socketio.interfaces
from nti.socketio.dataserver_session import Session

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
		logger.debug("Unauthenticated session request")
		raise hexc.HTTPUnauthorized()
	# gevent.sleep( 0.1 ) # Trivial throttling
	logger.debug("Creating session handler for '%s'", username)

	session_manager = component.getUtility(IDataserver).session_manager
	session = session_manager.create_session(session_class=Session, owner=username)
	session.originating_site_names = site_policies.get_possible_site_names(request, include_default=True)
	logger.debug("Created new session %s with site policies %s", session, session.originating_site_names)
	return session

POSSIBLE_TRANSPORTS = {'websocket', 'flashsocket', 'xhr-polling', 'jsonp-polling', 'htmlfile'}
SUPPORTED_TRANSPORTS = {'websocket': 1,
						'xhr-polling': 2}

#: Twice as long as our ping time
CLIENT_TIMEOUT_IN_SECONDS = 60

@view_config(route_name=RT_HANDSHAKE)  # POST or GET
def _handshake_view(request):
	"""
	The first step in socket.io. A handshake begins the process by
	requesting a new session, we send back the session id and some miscellaneous
	information.
	"""
	session = _create_new_session(request)

	# session_id:heartbeat_seconds:close_timeout:supported_type, supported_type,...
	handler_types = [x[0] for x in component.getAdapters((request,),
														  nti.socketio.interfaces.ISocketIOTransport)
					 if x[0] in SUPPORTED_TRANSPORTS]
	handler_types = sorted(handler_types, key=lambda x: SUPPORTED_TRANSPORTS.get(x, -1))
	# The two client side timeouts (heartbeat/close) essentially act the same;
	# if either fires, the client will request a new session for the server.
	data = "%s:%s:%s:%s" % (session.session_id,
							CLIENT_TIMEOUT_IN_SECONDS,
							CLIENT_TIMEOUT_IN_SECONDS,
							",".join(handler_types))
	data = data.encode('ascii')
	# NOTE: We are not handling JSONP here. It should not be a registered transport

	response = request.response
	response.body = data
	response.content_type = b'text/plain'
	return response

@interface.implementer(IWSWillUpgradeVeto)
class _WSWillUpgradeVeto(object):
	"""
	A veto handler to avoid upgrading to websockets if the session doesn't
	exist. This lets our 404 propagate.
	"""

	def __init__(self, evt=None):
		return

	def can_upgrade(self, wswill_upgrade_event):
		"""
		If the session exists and is valid, we can upgrade.
		"""
		# Pull the session id out of the path. See URL_CONNECT
		environ = wswill_upgrade_event.environ
		sid = environ['PATH_INFO'].split('/')[-1]
		def test_can_upgrade():
			try:
				_get_session(sid)
			except hexc.HTTPNotFound:
				logger.debug("Not upgrading, no session", exc_info=True)
				return False
			else:
				return True
		# NOTE: Not running this in any site policies.
		# This veto does not run in our transaction tween.
		tx_runner = component.getUtility(IDataserverTransactionRunner)
		result = tx_runner(test_can_upgrade, retries=3, sleep=0.1)
		return result

def _get_session(session_id):
	"""
	Returns a valid session to use, or raises HTTPNotFound.
	"""
	try:
		ds = component.getUtility(IDataserver)
		# We want to be as lightweight as possible here (no writes).
		session = ds.session_manager.get_session(session_id,
												 cleanup=False,
												 incr_hits=False)
	except (KeyError, ValueError):
		logger.warn("Client sent bad value for session (%s); DDoS attempt?", session_id, exc_info=True)
		raise hexc.HTTPNotFound(_("No session found or illegal session id"))

	if session is None:
		raise hexc.HTTPNotFound("No session found for %s" % session_id)
	if not session.owner:
		logger.warn("Found session with no owner. Cannot connect: %s", session)
		raise hexc.HTTPNotFound("Session has no owner %s" % session_id)
	return session

from .tweens.greenlet_runner_tween import HTTPOkGreenletsToRun

@view_config(route_name=RT_CONNECT)  # Any request method
def _connect_view(request):

	environ = request.environ
	transport = request.matchdict.get('transport')
	ws_transports = ('websocket',)
	session_id = request.matchdict.get('session_id')

	# All our errors need to come back as 404 (not 403) otherwise the browser
	# keeps trying to reconnect this same session
	if (transport in ws_transports and 'wsgi.websocket' not in environ)\
		or (transport not in ws_transports and 'wsgi.websocket' in environ):
		# trying to use an upgraded websocket on something that is not websocket transport,
		# or vice/versa
		raise hexc.HTTPNotFound('Incorrect use of websockets')

	session = _get_session(session_id)

	# Users must be authenticated. All users are allowed to make connections
	# So this is a hamfisted way of achieving that policy.
	if not request.authenticated_userid:
		raise hexc.HTTPUnauthorized()

	# Make the session object available for WSGI apps
	environ['socketio'] = session.socket
	environ['socketio'].session = session  # TODO: Needed anymore?

	# Create a transport and handle the request likewise
	try:
		transport = component.getAdapter(request,
										 nti.socketio.interfaces.ISocketIOTransport,
										 name=transport)
	except LookupError:
		raise hexc.HTTPNotFound("Unknown transport type %s" % transport)

	request_method = environ.get("REQUEST_METHOD")
	try:
		jobs_or_response = transport.connect(session, request_method)
	except IOError:
		logger.debug("Client disconnected during connection", exc_info=True)
		raise hexc.HTTPClientError()

	if IResponse.providedBy(jobs_or_response):
		return jobs_or_response

	# If we have connection jobs (websockets)
	# we need to stay in this call stack so that the
	# socket is held open for reading by the server
	# and that the events continue to fire for it
	# (Other things might be in that state too)
	# We have to close the connection and commit the transaction
	# if we do expect to stick around a long time.
	# We do this by cooperating with the greenlet_runner_tween
	# and letting the stack unwind as normal.
	greenlets_to_run = HTTPOkGreenletsToRun()
	greenlets_to_run.greenlets = jobs_or_response
	greenlets_to_run.response = request.response

	transaction.get().addAfterCommitHook(_kill_transport_jobs_on_failed_commit,
										 args=(transport, jobs_or_response))

	# TODO: If this process raises and we wind up hitting the retry logic,
	# how does this react? Badly probably
	return greenlets_to_run

def _kill_transport_jobs_on_failed_commit(success, transport, jobs):
	# Not a closure to be sure what we capture
	if not success:
		logger.debug("Killing transport and jobs on commit failure")
		transport.kill()
		for job in jobs:
			job.kill()
