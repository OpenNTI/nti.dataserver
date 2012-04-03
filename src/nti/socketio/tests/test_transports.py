#!/usr/bin/env python
#pylint: disable=R0904
from hamcrest import (assert_that, is_, has_length, only_contains, has_property, has_item, has_entry,
					  not_none)

import contextlib
import gevent
import transaction

from nti.socketio import transports as socketio_server
from gevent.queue import Queue
import nti.socketio.protocol
protocol = nti.socketio.protocol
import nti.socketio.transports as transports

from nti.appserver.tests import ConfiguringTestBase
from nti.dataserver.tests import mock_dataserver

from pyramid.testing import DummyRequest

class TestWebSocket(ConfiguringTestBase):
	@mock_dataserver.WithMockDS
	def test_websocket_transport_greenlets(self):
		class WebSocket(object):
			server = None
			def __init__( self ):
				self.queue = Queue()

			def send(self, msg):
				pass
			def wait(self):
				return self.queue.get()

		class Handler(object):
			server, session_manager, set_proxy_session, context_manager_callable, handling_session_cm = [None] * 5
			def __init__(self):
				self.environ = {}

		class Mock(object):
			server, session_manager, set_proxy_session, context_manager_callable, handling_session_cm, get_session = [None] * 6
			session_id, incr_hits = [None] * 2


		websocket = WebSocket()
		handler = Handler()
		handler.environ['wsgi.websocket'] = websocket
		handler.environ['socketio'] = nti.socketio.protocol.SocketIOSocket(None)

		handler.server = Mock()
		handler.server.session_manager = Mock()
		self.ds.session_manager = handler.server.session_manager
		handler.server.session_manager.set_proxy_session = lambda x, y: None

		def cm(): yield
		handler.context_manager_callable = contextlib.contextmanager( cm )
		handler.handling_session_cm = Mock()
	#	handler.handling_session_cm.premature_exit_but_its_okay = lambda: 1


		transport = socketio_server.WebsocketTransport(handler)
		transport.handler = handler

		sess = Mock()
		sess.session_id = 1
		sess.incr_hits = lambda: 1
		handler.server.session_manager.get_session = lambda x: sess

		jobs = transport.connect( sess, ping_sleep=0.1 )
		gevent.sleep( )
		assert_that( jobs, has_length( 3 ) )
		assert_that( jobs, only_contains( has_property( 'started', True ) ) )
		for job in jobs:
			assert_that( job.ready(), is_(False) )

		# Sending in a None from the "socket" kills all jobs
		websocket.queue.put( None )
		gevent.sleep( 0.2 )
		for job in jobs:
			assert_that( job.ready(), is_( True ) )


class MockSession(object):
	socket = None
	session_confirmed = None
	heartbeats = None
	killed = None
	server_messages = ()
	connection_confirmed = False
	
	def heartbeat(self):
		self.heartbeats = (self.heartbeats or 0) + 1

	def kill( self ):
		self.killed = True

	def put_server_msg( self, msg ):
		if not self.server_messages:
			self.server_messages = [msg]
		else:
			self.server_messages.append( msg )

	client_msgs = ()
	def get_client_msgs( self ):
		return self.client_msgs

	def clear_disconnect_timeout(self): pass

class MockSocket(object):
	protocol = None



class TestXHRTransport(ConfiguringTestBase):

	def setUp(self):
		super(TestXHRTransport,self).setUp()

		session = MockSession()
		socket = MockSocket()
		session.socket = socket

		socket.protocol = protocol.SocketIOProtocolFormatter1()

		request = DummyRequest()
		transport = transports.XHRPollingTransport( request )
		self.request = transport.request
		self.transport = transport
		self.session = session

	def test_options(self):
		assert_that( self.transport.options(self.session), not_none() )

	def test_post_heartbeat(self):
		self.request.body = b"2::"
		response = self.transport.post( self.session )

		assert_that( self.session, has_property( 'heartbeats', 1 ) )
		assert_that( response.body, is_( self.session.socket.protocol.make_noop() ) )

	def test_post_kill( self ):
		self.request.body = b"0::"
		response = self.transport.post( self.session )

		assert_that( self.session, has_property( 'killed', True ) )
		assert_that( response.body, is_( self.session.socket.protocol.make_noop() ) )

	def test_post_event( self ):
		self.request.body = self.session.socket.protocol.make_event( 'foo' )
		response = self.transport.post( self.session )

		assert_that( self.session, has_property( 'server_messages',
												 has_item( has_entry( 'name', 'foo' ) ) ) )
		assert_that( response.body, is_( self.session.socket.protocol.make_noop() ) )


	def test_post_bad_data_kills_transaction( self ):
		transaction.begin()
		with self.assertRaises( ValueError ):
			self.transport.post( self.session )

		assert_that( transaction.isDoomed(), is_( True ) )

	@mock_dataserver.WithMockDS
	def test_connect_fresh(self):
		self.request.body = b"1::"
		self.transport.connect( self.session, 'POST' )

		assert_that( self.session, has_property( 'connection_confirmed', True ) )

		# Now that it's confirmed, we'll go into a get
		self.session.client_msgs = [self.session.socket.protocol.make_event('foo')]

		rsp = self.transport.connect( self.session, 'GET' )
		assert_that( rsp.body, is_( self.session.client_msgs[0] ) )
