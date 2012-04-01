#!/usr/bin/env python

from hamcrest import (assert_that, is_, has_length, only_contains, has_property)

import contextlib
import gevent

from nti.appserver import dataserver_socketio_views as socketio_server
from gevent.queue import Queue
import socketio.protocol

from nti.appserver.tests import ConfiguringTestBase
from nti.dataserver.tests import mock_dataserver

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
		handler.environ['socketio'] = socketio.protocol.SocketIOProtocol(None)

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
