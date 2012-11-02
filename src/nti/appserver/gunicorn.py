#!/usr/bin/env python
"""
Support for running the application with gunicorn.

You must use our worker (:class:`GeventApplicationWorker`), configured with paster::

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

from pyramid.security import unauthenticated_userid
from pyramid.threadlocal import get_current_request


import gunicorn.workers.ggevent as ggevent
#import gunicorn.http.wsgi
#import gunicorn.sock

import gevent
import gevent.socket

from .application_server import FlashPolicyServer
from .application_server import WebSocketServer

from zope.dottedname import resolve as dottedname

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
		address = ('0.0.0.0', getattr(cfg, 'flash_policy_server_port', FlashPolicyServer.NONPRIV_POLICY_PORT) )
		def __getattr__( self, name ):
			return getattr( cfg, name )
	conf = FlashConf( )

	# get it only once
	addr = conf.address
	sock_type = TCP6Socket if util.is_ipv6(addr[0]) else TCPSocket

	try:
		result = sock_type(conf, log)
		log.info( "Listening at %s", result )
		return result
	except socket.error, e: # pragma: no cover
		if e[0] == errno.EADDRINUSE:
			log.error("Connection in use: %s", str(addr))
		elif e[0] == errno.EADDRNOTAVAIL:
			log.error("Invalid address: %s", str(addr))

		raise

# class _PhonyRequest(object):
# 	headers = ()
# 	input_buffer = None
# 	typestr = None
# 	uri = None
# 	path = None
# 	version = (1,0)
# 	proxy_protocol_info = None # added in 0.15.0
# 	def get_input_headers(self):
# 		raise Exception("Not implemented for phony request")


class _PyWSGIWebSocketHandler(WebSocketServer.handler_class,ggevent.PyWSGIHandler):
	"""
	Our handler class combines pywsgi's custom logging and environment setup with
	websocket request upgrading. Order of inheritance matters.
	"""

	# JAM 20121002: The below is all from pre-gunicorn 0.15.0. It actually seems
	# to have been unnecessary in 0.14.6 as well. At any rate, unit, gp and int
	# tests all pass without this code in place, and inspection of the referenced
	# classes and workers doesn't reveal a need for it: the gevent worker extends
	# the Async worker, and the proxy/forward handling is done in gunicorn.http.wsgi.
	# We'll know for sure if the logs look...odd...in the proxied environments

	# # Things to copy out of the our prepared environment
	# # into the environment created by the super's get_environment
	# ENV_TO_COPY = (b'RAW_URI', b'wsgi.errors', b'wsgi.file_wrapper',
	# 			   b'REMOTE_ADDR',b'SERVER_SOFTWARE',
	# 			   b'SERVER_NAME', b'SERVER_PORT',
	# 			   b'wsgi.url_scheme')


	# # We are using the SocketIO server and the Gevent Worker
	# # Only the Sync and Async workers setup the environment
	# # and deal with things like x-forwarded-for. So we
	# # must override the default pywsgi environment creation
	# # to use that provided by gunicorn to get these features
	# # The plain WSGIHandler uses prepare_env. The pywsgi handler
	# # uses get_environ
	# def prepare_env(self):
	# 	req = self.request
	# 	req.body = req.input_buffer
	# 	req.method = req.typestr
	# 	if b'?' in req.uri:
	# 		_, query = req.uri.split(b'?', 1)
	# 	else:
	# 		_, query = req.uri, b''
	# 	req.query = query
	# 	req.headers = getattr( req, 'headers', None ) or req.get_input_headers()
	# 	_, env = gunicorn.http.wsgi.create(req, self.socket, self.client_address, worker.address, worker.cfg)
	# 	return env


	# def get_environ(self):
	# 	if not getattr( self, 'request', None ):
	# 		# gevent.pywsgi can call this before gunicorn has a chance to
	# 		# assign a request object.
	# 		self.request = _PhonyRequest()
	# 		self.request.typestr = self.command
	# 		self.request.uri = self.path
	# 		self.request.headers = []
	# 		self.request.path = self.path
	# 		for header in self.headers.headers:
	# 			# If we're not careful to split with a byte string here, we can
	# 			# run into UnicodeDecodeErrors: True, all the headers are supposed to be sent
	# 			# in ASCII, but frickin IE (at least 9.0) can send non-ASCII values,
	# 			# without url encoding them, in the value of the Referer field (specifically
	# 			# seen when it includes a fragment in the URI, which is also explicitly against
	# 			# section 14.36 of HTTP 1.1. Stupid IE).
	# 			k, v = header.split( b':', 1)
	# 			self.request.headers.append( (k.upper(), v.strip()) )


	# 	env = self.prepare_env()
	# 	# This does everything except it screws with REMOTE_ADDR
	# 	# and some other values we want gunicorn to rule
	# 	ws_env = super(HandlerClass,self).get_environ()
	# 	for k in self.ENV_TO_COPY:
	# 		ws_env[k] = env[k]
	# 	ws_env[b'gunicorn.sock'] = self.socket
	# 	ws_env[b'gunicorn.socket'] = self.socket
	# 	return ws_env


class GeventApplicationWorker(ggevent.GeventPyWSGIWorker):
	"""
	Our application worker.
	"""

	#: We need to be served by something that can handle websockets
	server_class = WebSocketServer

	#: Our custom server requires a custom handler.
	wsgi_handler = _PyWSGIWebSocketHandler


	app_server = None
	app = None
	server_class = None
	socket = None
	policy_server = None
	_preloaded_app = None

	@classmethod
	def setup(cls): # pragma: no cover
		"""
		We cannot patch the entire system to work with gevent due to
		issues with ZODB (but see application.py). Instead, we patch
		just our socket when we create it. So this method DOES NOT call
		super (which patches the whole system).
		"""
		import nti.monkey.gevent_patch_on_import # But we do import the patches, to make sure we get the patches we do want


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

		if getattr( self.cfg, 'preload_app', None ): # pragma: no cover
			logger.warn( "Preloading app before forking not supported" )


	def _init_server( self ):
		try:
			dummy_app = self.app.app
			wsgi_app = loadwsgi.loadapp( 'config:' + dummy_app.global_conf['__file__'], name='dataserver_gunicorn' )
			self.app_server = WebSocketServer(
				(dummy_app.kwargs.get( 'host', ''), int(dummy_app.global_conf['http_port'])),
				wsgi_app,
				handler_class=self.wsgi_handler)
		except Exception:
			logger.exception( "Failed to create appserver" )
			raise

	def init_process(self, _call_super=True):
		"""
		We must create the appserver only once, and only after the process
		has forked if we are using ZEO; even though we do not have pthreads that fail to survive
		the fork, the asyncore connection and ZODB cache do not work properly when forked.

		Also, we have ZMQ background threads. So even if we have, say RelStorage and no ZEO threads,
		we can still fail to fork properly.
		"""
		gevent.hub.get_hub() # init the hub in this new thread/process
		if not self._preloaded_app:
			logger.info( "Loading app after forking" )
			self._init_server()

		# Change/update the logging format.
		# It's impossible to configure this from the ini file because
		# Paste uses plain ConfigParser, which doesn't understand escaped % chars,
		# and tries to interpolate the settings for the log file.
		# For now, we just add on the time in seconds and  microseconds with %(T)s.%(D)s. Other options include
		# using a different key with a fake % char, like ^,
		# (Note: microseconds and seconds are not /total/, they are each fractions.)
		# (Note: See below for why this must be sure to be a byte string: Frickin IE in short)
		self.cfg.settings['access_log_format'].set( str(self.cfg.access_log_format) + b" %(T)s.%(D)ss" )
		# Also, if there is a handler set for the gunicorn access log (e.g., '-' for stderr)
		# Then the default propagation settings mean we get two copies of access logging.
		# make that stop.
		gun_logger = logging.getLogger( 'gunicorn.access' )
		if gun_logger.handlers: # pragma: no cover
			gun_logger.propagate = False

		self.server_class = _ServerFactory( self )
		self.socket = gevent.socket.socket(_sock=self.socket)
		self.app_server.socket = self.socket
		# Everything must be complete and ready to go before we call into
		# the super, it in turn calls run()
		# TODO: Errors here get silently swallowed and gunicorn just cycles the worker
		if _call_super: # pragma: no cover
			super(GeventApplicationWorker,self).init_process()




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

		if False: # pragma: no cover
			def print_stacks():
				from nti.appserver._util import dump_stacks
				import sys
				while True:
					gevent.sleep( 15.0 )
					print( '\n'.join( dump_stacks() ), file=sys.stderr )

			gevent.spawn( print_stacks )

		# The super class will provide a Pool based on the
		# worker_connections setting
		assert spawn is not None
		class WorkerGreenlet(spawn.greenlet_class):
			"""
			See nti.dataserver for this. We provide a pretty thread name to the extent
			possible.
			"""

			def __thread_name__(self):
				# The WorkerGreenlets themselves are cached and reused,
				# but the request we can cache on
				prequest = get_current_request()
				if not prequest:
					return self._formatinfo()

				try:
					return getattr( prequest, '_worker_greenlet_cached_thread_name' )
				except AttributeError:
					pass
				cache = False
				try:
					uid = unauthenticated_userid( prequest )
					cache = True
				except LookupError: # pragma: no cover
					# In some cases, pyramid tries to turn this into an authenticated
					# user id, and if it's too early, we won't be able to use the dataserver
					uid = prequest.remote_user

				result = "%s:%s" % (prequest.path, uid or '' )
				if cache:
					setattr( prequest, '_worker_greenlet_cached_thread_name', result )
				return result

		spawn.greenlet_class = WorkerGreenlet
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

		# JAM 20121102: See above. This class actually doesn't really do anything anymore.
		# except act as multiple inheritance. We also can set it up statically

		# Now, for logging to actually work, we need to replace
		# the handler class with one that sets up the required values in the
		# environment, as per ggevent.

		assert worker.app_server.handler_class is _PyWSGIWebSocketHandler
		worker.app_server.base_env = ggevent.PyWSGIServer.base_env
		return worker.app_server
