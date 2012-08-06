#!/usr/bin/env python2.7
"""
Support for running the application with gunicorn. You must use our worker, configured with paster:
	[server:main]
	use = egg:gunicorn#main
	host =
	port = %(http_port)s
	worker_class =  nti.appserver.gunicorn.GeventApplicationWorker
	workers = 1
"""

from __future__ import print_function, unicode_literals, absolute_import

import logging
logger = logging.getLogger(__name__)

import socket
import errno

import gunicorn.workers.ggevent as ggevent
import gunicorn.http.wsgi
import gunicorn.sock

import gevent
import gevent.socket
from gevent.server import StreamServer

from zope.dottedname import resolve as dottedname

import nti.appserver.standalone
from paste.deploy import loadwsgi

class _DummyApp(object):
	global_conf = None
	kwargs = None

def dummy_app_factory(global_conf, **kwargs):
	"""
	A Paste app factory that exists to bootstrap the process
	in the master gunicorn instance. Individual worker instances will
	create their own application; the objects returned here simply
	echo configuration.
	"""
	app = _DummyApp()
	app.global_conf = global_conf
	app.kwargs = kwargs
	return app

def _create_flash_socket(cfg, log):
	"""
	Create a new socket for the flash policy server (which has to run on a known TCP port)
	Cribbed from :func:`gunicorn.sock.create_socket`, but without
	the retries, looking for an existing file descriptor,
	and the call to sys.exit on failure.

	:raises socket.error: If we fail to create the socket.

	"""
	# We cannot use create_socket directly (naively), as it fails the integration tests if something is
	# already using that port (a real instance): it calls sys.exit().
	# Plus it wants to reuse an existing FD in the environment, which would be the
	# wrong one.

	util = dottedname.resolve( 'gunicorn.util' )
	TCP6Socket = dottedname.resolve( 'gunicorn.sock.TCP6Socket' )
	TCPSocket = dottedname.resolve( 'gunicorn.sock.TCPSocket' )

	class FlashConf(object):
		address = ('0.0.0.0',10843)
		def __getattr__( self, name ):
			return getattr( cfg, name )
	conf = FlashConf( )

	# get it only once
	addr = conf.address

	if util.is_ipv6(addr[0]):
		sock_type = TCP6Socket
	else:
		sock_type = TCPSocket

	try:
		result = sock_type(conf, log)
		log.info( "Listening at %s", result )
		return result
	except socket.error, e:
		if e[0] == errno.EADDRINUSE:
			log.error("Connection in use: %s", str(addr))
		elif e[0] == errno.EADDRNOTAVAIL:
			log.error("Invalid address: %s", str(addr))

		raise



class GeventApplicationWorker(ggevent.GeventPyWSGIWorker):

	app_server = None
	app = None
	server_class = None
	socket = None
	policy_server = None

	@classmethod
	def setup(cls):
		"""
		We cannot patch the entire system to work with gevent due to
		issues with ZODB (but see application.py). Instead, we patch
		just our socket when we create it. So this method DOES NOT call
		super (which patches the whole system).
		"""
		pass


	def __init__( self, *args, **kwargs ):
		# These objects are instantiated by the master process (arbiter)
		# in the parent process, pre-fork, once for every worker
		super(GeventApplicationWorker,self).__init__( *args, **kwargs )
		# Now we have access to self.cfg and the rest
		policy_server_sock = getattr( self.cfg, 'policy_server_sock', None )
		if policy_server_sock is None:
			try:
				self.cfg.policy_server_sock = _create_flash_socket( self.cfg, logger )
			except socket.error:
				logger.error( "Failed to create flash policy socket" )


	def init_process(self):
		"""
		We must create the appserver only once, and only after the process
		has forked. Doing it before the fork leads to thread-related problems
		and a deadlock (the ZEO connection pthreads do not survive the fork, I think).
		"""

		try:
			gevent.hub.get_hub() # init the hub in this new thread/process
			dummy_app = self.app.app
			wsgi_app = loadwsgi.loadapp( 'config:' + dummy_app.global_conf['__file__'], name='dataserver_gunicorn' )
			# Note that this is creating the SockeIO server class as well as initializing
			# the Pyramid/Dataserver application
			self.app_server = nti.appserver.standalone._create_app_server( wsgi_app,
																		   dummy_app.global_conf,
																		   port=dummy_app.global_conf['http_port'],
																		   **dummy_app.kwargs )
			self.wsgi_handler = self.app_server.handler_class

		except Exception:
			logger.exception( "Failed to create appserver" )
			raise


		# Change/update the logging format.
		# It's impossible to configure this from the ini file because
		# Paste uses plain ConfigParser, which doesn't understand escaped % chars,
		# and tries to interpolate the settings for the log file.
		# For now, we just add on the time in microseconds with %(D)s. Other options include
		# using a different key with a fake % char, like ^,
		self.cfg.settings['access_log_format'].set( self.cfg.access_log_format + " %(D)sus" )
		# Also, if there is a handler set for the gunicorn access log (e.g., '-' for stderr)
		# Then the default propagation settings mean we get two copies of access logging.
		# make that stop.
		gun_logger = logging.getLogger( 'gunicorn.access' )
		if gun_logger.handlers:
			gun_logger.propagate = False

		self.server_class = _ServerFactory( self )
		self.socket = gevent.socket.socket(_sock=self.socket)
		self.app_server.socket = self.socket
		# Everything must be complete and ready to go before we call into
		# the super, it in turn calls run()
		super(GeventApplicationWorker,self).init_process()

class _PhonyRequest(object):
	headers = ()
	input_buffer = None
	typestr = None
	uri = None
	path = None
	version = (1,0)
	def get_input_headers(self):
		raise Exception("Not implemented for phony request")

class _ServerFactory(object):
	"""
	Given a worker that has already created the app server, does
	what's necessary to finish initializing it for running (such as
	messing with socket blocking and adjusting handler classes).
	Serves as the 'server_class' value.
	"""

	def __init__( self, worker ):
		self.worker = worker


	def __call__( self,  socket, application=None, spawn=None, log=None,
				  handler_class=None):
		worker = self.worker
		# Launch the flash policy listener if we could create it
		policy_server_sock = getattr( worker.cfg, 'policy_server_sock', None )
		if policy_server_sock is not None:
			worker.policy_server = FlashPolicyServer( policy_server_sock )
			policy_server_sock.setblocking( 0 )
			worker.policy_server.start()
			logger.info( "Created flash policy server on %s", policy_server_sock )

		# The super class will provide a Pool based on the
		# worker_connections setting
		worker.app_server.set_spawn(spawn)
		# We want to log with the appropriate logger, which
		# has monitoring info attached to it
		worker.app_server.log = log

		# The super class will set the socket to blocking because
		# it thinks it has monkey patched the system. It hasn't.
		# Therefore the socket must be non-blocking or we get
		# the dreaded 'cannot switch to MAINLOOP from MAINLOOP'
		# (Non blocking is how gevent's baseserver:_tcp_listener sets things up)
		worker.app_server.socket.setblocking(0)
		# Now, for logging to actually work, we need to replace
		# the handler class with one that sets up the required values in the
		# environment, as per ggevent.

		class HandlerClass(worker.app_server.handler_class,ggevent.PyWSGIHandler):
			request = None

			# Things to copy out of the our prepared environment
			# into the environment created by the super's get_environment
			ENV_TO_COPY = ('RAW_URI', 'wsgi.errors', 'wsgi.file_wrapper',
						   'REMOTE_ADDR','SERVER_SOFTWARE',
						   'SERVER_NAME', 'SERVER_PORT',
						   'wsgi.url_scheme')


			# We are using the SocketIO server and the Gevent Worker
			# Only the Sync and Async workers setup the environment
			# and deal with things like x-forwarded-for. So we
			# must override the default pywsgi environment creation
			# to use that provided by gunicorn to get these features
			# The plain WSGIHandler uses prepare_env. The pywsgi handler
			# uses get_environ
			def prepare_env(self):
				req = self.request
				req.body = req.input_buffer
				req.method = req.typestr
				if '?' in req.uri:
					_, query = req.uri.split('?', 1)
				else:
					_, query = req.uri, ''
				req.query = query
				req.headers = getattr( req, 'headers', None ) or req.get_input_headers()
				_, env = gunicorn.http.wsgi.create(req, self.socket, self.client_address, worker.address, worker.cfg)
				return env


			def get_environ(self):
				if not getattr( self, 'request', None ):
					# gevent.pywsgi can call this before gunicorn has a chance to
					# assign a request object.
					self.request = _PhonyRequest()
					self.request.typestr = self.command
					self.request.uri = self.path
					self.request.headers = []
					self.request.path = self.path
					for header in self.headers.headers:
						k, v = header.split( ':', 1)
						self.request.headers.append( (k.upper(), v.strip()) )


				env = self.prepare_env()
				# This does everything except it screws with REMOTE_ADDR
				# and some other values we want gunicorn to rule
				ws_env = super(HandlerClass,self).get_environ()
				for k in self.ENV_TO_COPY:
					ws_env[k] = env[k]
				ws_env['gunicorn.sock'] = self.socket
				ws_env['gunicorn.socket'] = self.socket
				return ws_env


		worker.app_server.handler_class = HandlerClass
		worker.app_server.base_env = ggevent.PyWSGIServer.base_env
		return worker.app_server

class FlashPolicyServer(StreamServer):
	policy = b"""<?xml version="1.0" encoding="utf-8"?>
	<!DOCTYPE cross-domain-policy SYSTEM "http://www.macromedia.com/xml/dtds/cross-domain-policy.dtd">
	<cross-domain-policy>
		<allow-access-from domain="*" to-ports="*"/>
	</cross-domain-policy>\n"""

	def __init__(self, listener=None, backlog=None):
		if listener is None:
			listener = ('0.0.0.0', 10843)
		StreamServer.__init__(self, listener=listener, backlog=backlog)

	def handle(self, socket, address):
		socket.sendall(self.policy)
