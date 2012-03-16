#!/usr/bin/env python

from hamcrest import (assert_that, is_, has_length, only_contains, has_property)

import contextlib
import gevent

from nti.dataserver import socketio_server
from gevent.queue import Queue

def test_websocket_transport_greenlets():
	class WebSocket(object):
		def __init__( self ):
			self.queue = Queue()

		def send(self, msg):
			pass
		def wait(self):
			return self.queue.get()

	class Handler(object):
		def __init__(self):
			self.environ = {}

	class Mock(object): pass

	websocket = WebSocket()
	handler = Handler()
	handler.environ['wsgi.websocket'] = websocket
	handler.server = Mock()
	handler.server.session_manager = Mock()
	handler.server.session_manager.set_proxy_session = lambda x, y: None
	
	def cm(): yield
	handler.context_manager_callable = contextlib.contextmanager( cm )
	handler.handling_session_cm = Mock()
	handler.handling_session_cm.premature_exit_but_its_okay = lambda: 1


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
