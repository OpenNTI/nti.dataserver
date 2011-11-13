import sys
import uuid
import traceback
import gevent
from socket import error

from gevent.pywsgi import WSGIServer
from gevent.queue import Queue
from gevent.event import Event
from socketio.protocol import SocketIOProtocol
from socketio.handler import SocketIOHandler
from socketio.policyserver import FlashPolicyServer

import anyjson as json

__all__ = ['SocketIOServer']

class SocketIOServer(WSGIServer):
	"""A WSGI Server with a resource that acts like an SocketIO."""

	def __init__(self, *args, **kwargs):
		self.sessions = {}
		self.namespace = kwargs.pop('namespace')

		if kwargs.pop('policy_server', True):
			self.policy_server = FlashPolicyServer()
		else:
			self.policy_server = None

		kwargs['handler_class'] = SocketIOHandler
		super(SocketIOServer, self).__init__(*args, **kwargs)

	def start_accepting(self):
		if self.policy_server is not None:
			try:
				self.policy_server.start()
			except error, ex:
				sys.stderr.write('FAILED to start flash policy server: %s\n' % (ex, ))
			except Exception:
				traceback.print_exc()
				sys.stderr.write('FAILED to start flash policy server.\n\n')
		super(SocketIOServer, self).start_accepting()

	def kill(self):
		if self.policy_server is not None:
			self.policy_server.kill()
		super(SocketIOServer, self).kill()

	def handle(self, socket, address):
		handler = self.handler_class(socket, address, self)
		self.set_environ({'socketio': SocketIOProtocol(handler)})
		handler.handle()

	def get_session(self, session_id=''):
		"""Return an existing or new client Session."""

		session = self.sessions.get(session_id)

		if session is None:
			session = Session( self )
			self.sessions[session.session_id] = session
		else:
			session.incr_hits()

		return session

	def kill_session( self, session ):
		"""Kills an existing session or session id. Removes it from the store."""
		if hasattr( session, 'session_id' ):
			self.sessions.pop( session.session_id, None )
			session.kill()
		elif session in self.sessions:
			self.kill_session( self.sessions[session] )


class Session(object):
	"""
	Client session which checks the connection health and the queues for
	message passing.
	`self.owner`: An attribute for the user that owns the session.
	"""

	STATE_NEW = "NEW"
	STATE_CONNECTED = "CONNECTED"
	STATE_DISCONNECTING = "DISCONNECTING"
	STATE_DISCONNECTED = "DISCONNECTED"

	def __init__(self,server=None):
		self.session_id = uuid.uuid4().urn.replace( ':', '_' )
		self.client_queue = Queue() # queue for messages to client
		self.server_queue = Queue() # queue for messages to server
		self.hits = 0
		self.heartbeats = 0
		self.timeout = Event()
		self.wsgi_app_greenlet = None
		self.state = "NEW"
		self.connection_confirmed = False
		self.server = server
		# NTIExtensions
		self.owner = None
		self.event_handlers = {}
		self.externalize_function = json.dumps
		self.internalize_function = json.loads

		def disconnect_timeout():
			self.timeout.clear()
			if self.timeout.wait(10.0):
				gevent.spawn(disconnect_timeout)
			else:
				self.kill()
		gevent.spawn(disconnect_timeout)

	def __str__(self):
		result = ['[session_id=%r' % self.session_id]
		if self.state == self.STATE_CONNECTED:
			result.append('connected')
		if self.client_queue.qsize():
			result.append('client_queue[%s]' % self.client_queue.qsize())
		if self.server_queue.qsize():
			result.append('server_queue[%s]' % self.server_queue.qsize())
		if self.hits:
			result.append('hits=%s' % self.hits)
		if self.heartbeats:
			result.append('heartbeats=%s' % self.heartbeats)
		result.append( 'confirmed=%s' % self.connection_confirmed )
		result.append( 'id=%s]'% id(self) )
		return ' '.join(result)

	def new_protocol( self, handler=None ):
		p = SocketIOProtocol( handler )
		p.session = self
		return p

	protocol_handler = property(new_protocol)

	@property
	def connected(self):
		return self.state == self.STATE_CONNECTED

	def incr_hits(self):
		self.hits += 1

		if self.hits == 1:
			self.state = self.STATE_CONNECTED

	def clear_disconnect_timeout(self):
		self.timeout.set()

	def heartbeat(self):
		self.clear_disconnect_timeout()

	def kill(self):
		if self.connected:
			self.state = self.STATE_DISCONNECTING
			self.server_queue.put_nowait(None)
			self.client_queue.put_nowait(None)
			self.server.kill_session( self )
			#gevent.kill(self.wsgi_app_greenlet)
		else:
			pass # Fail silently

	def put_server_msg(self, msg):
		self.clear_disconnect_timeout()
		self.server_queue.put_nowait(msg)

	def put_client_msg(self, msg):
		self.clear_disconnect_timeout()
		self.client_queue.put_nowait(msg)

	def get_client_msg(self, **kwargs):
		return self.client_queue.get(**kwargs)

	def get_server_msg(self, **kwargs):
		return self.server_queue.get(**kwargs)
