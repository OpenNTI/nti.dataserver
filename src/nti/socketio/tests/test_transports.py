#!/usr/bin/env python
#pylint: disable=R0904
from hamcrest import (assert_that, is_, has_length, only_contains, has_property, has_item, has_entry,
					  not_none)

import contextlib
import gevent
import transaction

from nti.socketio import transports as socketio_server
from gevent.queue import Queue
from Queue import Empty
import nti.socketio.protocol
protocol = nti.socketio.protocol
import nti.socketio.transports as transports

from nti.appserver.tests import ConfiguringTestBase
from nti.dataserver.tests import mock_dataserver

from pyramid.testing import DummyRequest

class WebSocket(object):
	server = None
	def __init__( self ):
		self.queue = Queue()

	def send(self, msg):
		pass
	def receive(self):
		return self.queue.get()

class TestWebSocket(ConfiguringTestBase):
	@mock_dataserver.WithMockDS
	def test_websocket_transport_greenlets(self):


		class Handler(object):
			server, session_manager, set_proxy_session, context_manager_callable, handling_session_cm = [None] * 5
			def __init__(self):
				self.environ = {}

		class Mock(object):
			server, session_manager, set_proxy_session, context_manager_callable, handling_session_cm, get_session = [None] * 6
			session_id, incr_hits = [None] * 2
			socket = None
			protocol = None
			connected = True
			last_heartbeat_time = 0

		websocket = WebSocket()
		handler = Handler()
		handler.environ['wsgi.websocket'] = websocket
		handler.environ['socketio'] = nti.socketio.protocol.SocketIOSocket(None)

		handler.server = Mock()
		handler.server.session_manager = Mock()
		self.ds.session_manager = handler.server.session_manager
		handler.server.session_manager.proxy = {}
		def set_proxy_session(sid,prx):
			handler.server.session_manager.proxy[sid] = prx
		handler.server.session_manager.set_proxy_session = set_proxy_session
		def get_proxy_session(sid):
			return handler.server.session_manager.proxy[sid]
		handler.server.session_manager.get_proxy_session = get_proxy_session


		handler.handling_session_cm = Mock()
	#	handler.handling_session_cm.premature_exit_but_its_okay = lambda: 1


		transport = socketio_server.WebsocketTransport(handler)
		transport.handler = handler

		sess = Mock()
		sess.session_id = 1
		sess.incr_hits = lambda: 1
		handler.server.session_manager.get_session = lambda x: sess
		sess.socket = Mock()
		sess.socket.protocol = protocol.SocketIOProtocolFormatter1()

		jobs = transport.connect( sess, 'GET', ping_sleep=0.1 )
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

	@mock_dataserver.WithMockDS
	def test_sender(self):
		class Service(object):
			def get_session( self, sid ): return None

		proxy = socketio_server._WebsocketSessionEventProxy()
		sender = socketio_server.WebsocketTransport.WebSocketSender( 1, proxy, Service(), None )

		# Kill the session on a None-message
		assert_that( sender._do_send(), is_( False ) )
		transaction.begin()
		proxy.queue_message_to_client( None )
		transaction.commit()
		sender._run()
		with self.assertRaises( Empty ):
			proxy.get_client_msg(block=False)

	@mock_dataserver.WithMockDS
	def test_reader(self):
		class Socket(object):
			protocol = protocol.SocketIOProtocolFormatter1()
		class Session(object):
			last_heartbeat_time = 0
			connected = True
			killed = False
			socket = Socket()
			def kill(self):
				self.killed = True
		class Service(object):
			session = None
			def get_session( self, sid ): return self.session

		class WebSocket(object):
			def __init__(self): self.pkts = []
			def receive(self):
				return self.pkts.pop()

		proxy = socketio_server._WebsocketSessionEventProxy()
		socket = WebSocket()
		socket.pkts.append( None )
		socket.pkts.append( b'0::' )
		session = Session()
		service = Service()
		service.session = session

		reader = socketio_server.WebsocketTransport.WebSocketReader( 1, proxy, service, socket )


		reader._run()
		assert_that( session, has_property( 'killed', True ) )
		assert_that( reader, has_property( 'run_loop', False ) )

		session.killed = False
		reader.run_loop = True
		socket.pkts.append( 'unparsable' )

		reader._run()
		assert_that( session, has_property( 'killed', True ) )
		assert_that( reader, has_property( 'run_loop', False ) )

class MockSession(object):
	socket = None
	session_confirmed = None
	heartbeats = None
	killed = None
	server_messages = ()
	connection_confirmed = False
	session_id = 1

	def heartbeat(self):
		self.heartbeats = (self.heartbeats or 0) + 1

	def kill( self ):
		self.killed = True

	def queue_message_from_client( self, msg ):
		if not self.server_messages:
			self.server_messages = [msg]
		else:
			self.server_messages.append( msg )

	client_msgs = ()
	def get_messages_to_client( self ):
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

		class SessionService(object):
			def get_proxy_session(self,sid): return None
			def set_proxy_session(self,sid,sess): return None

		self.ds.session_manager = SessionService()
		self.session.client_msgs = ()
		self.transport.proxy_timeout = 0.01

		rsp = self.transport.connect( self.session, 'GET' )
		assert_that( rsp.body, is_( b'8::' ) )
