#!/usr/bin/env python
"""
Support for running the application with gunicorn.

You must use our worker (:class:`GeventApplicationWorker`), configured with paster::

	[server:main]
	use = egg:nti.dataserver#gunicorn
	host =
	port = %(http_port)s
	worker_class =  nti.appserver.gunicorn.GeventApplicationWorker
	workers = 1
"""

from __future__ import print_function, unicode_literals, absolute_import

import logging
logger = logging.getLogger(__name__)


from pyramid.security import unauthenticated_userid
from pyramid.threadlocal import get_current_request

import gunicorn
import gunicorn.workers.ggevent as ggevent
import gunicorn.http.wsgi
try:
	# gunicorn 0.17.2 finally finishes the process
	# of enforcing proper byte bodies (not unicode)
	# We should be fully compliant with this; make sure we're testing
	# with it. It also contains important performance optimizations
	if gunicorn.version_info < (0,17,2):
		raise ImportError("Gunicorn too old")
except AttributeError:
	raise ImportError("Gunicorn too old")

import gevent
import gevent.socket

from .application_server import FlashPolicyServer
from .application_server import WebSocketServer


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

class _PhonyRequest(object):
	headers = ()
	input_buffer = None
	typestr = None
	uri = None
	path = None
	query = None
	method = None
	body = None
	version = (1,0)
	proxy_protocol_info = None # added in 0.15.0
	def get_input_headers(self):
		raise Exception("Not implemented for phony request")


class _PyWSGIWebSocketHandler(WebSocketServer.handler_class,ggevent.PyWSGIHandler):
	"""
	Our handler class combines pywsgi's custom logging and environment setup with
	websocket request upgrading. Order of inheritance matters.
	"""

	# In gunicorn, an AsyncWorker defaults to handling requests itself, passing
	# them off to the application directly. Worker.handle goes to Worker.handle_request.
	# However, if you have a server_class involved, then that server entirely pre-empts
	# all the handling that the AsnycWorker would do. Since the Worker is what's aware
	# of the gunicorn configuration and calls gunicorn.http.wsgi.create to handle
	# getting the X-FORWARDED-PROTOCOL, etc, correct, it's important to do that.
	# Our worker uses a custom server, and we depend on that to be able to pass the right
	# information to gunicorn.http.wsgi.create

	def get_environ(self):
		# Start with what gevent creates
		environ = super(_PyWSGIWebSocketHandler,self).get_environ()
		# and then merge in anything that gunicorn wants to do instead

		request = _PhonyRequest()
		request.typestr = self.command
		request.uri = environ['RAW_URI']
		request.method = environ['REQUEST_METHOD']
		request.query = environ['QUERY_STRING']
		request.headers = []
		request.path = environ['PATH_INFO']
		request.body = environ['wsgi.input']
		for header in self.headers.headers:
			# If we're not careful to split with a byte string here, we can
			# run into UnicodeDecodeErrors: True, all the headers are supposed to be sent
			# in ASCII, but frickin IE (at least 9.0) can send non-ASCII values,
			# without url encoding them, in the value of the Referer field (specifically
			# seen when it includes a fragment in the URI, which is also explicitly against
			# section 14.36 of HTTP 1.1. Stupid IE).
			k, v = header.split( b':', 1)
			request.headers.append( (k.upper(), v.strip()) )

		# The request arrived on self.socket, which is also environ['gunicorn.sock']. This
		# is the "listener" argument as well that's needed for deriving the "HOST" value, if not present
		_, gunicorn_env = gunicorn.http.wsgi.create(request, self.socket, self.client_address, self.socket.getsockname(), self.server.worker.cfg)

		environ.update( gunicorn_env )
		return environ


class GeventApplicationWorker(ggevent.GeventPyWSGIWorker):
	"""
	Our application worker.
	"""

	#: Our custom server requires a custom handler.
	wsgi_handler = _PyWSGIWebSocketHandler

	app = None
	socket = None
	policy_server = None

	PREFERRED_MAX_CONNECTIONS = 100

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

	def _load_legacy_app( self ):
		try:
			if not isinstance( self.app, _PasterServerApplication ):
				logger.warn( "Deprecated code path, please update your .ini:\n[server:main]\nuse = egg:nti.dataserver#gunicorn" )
				dummy_app = self.app.app
				wsgi_app = loadwsgi.loadapp( 'config:' + dummy_app.global_conf['__file__'], name='dataserver_gunicorn' )
				self.app.app = wsgi_app
				self.app.callable = wsgi_app
		except Exception:
			logger.exception( "Failed to load app" )
			raise


	def init_process(self, _call_super=True):
		"""
		We must create the appserver only once, and only after the
		process has forked if we are using ZEO; the monkey-patched
		greenlet threads that ZEO spawned are still stopped and
		shutdown after the fork. Something also goes wrong with the
		ClientStorage._cache; in a nutshell, we need to close and reopen
		the database.

		At one time, we had ZMQ background threads. So even if we
		have, say RelStorage and no ZEO threads, we could still fail
		to fork properly. In theory this restriction is lifted as of
		20130130, but that combo needs tested.

		An additional problem is that at DNS (socket.getaddrinfo and
		friends) hangs after forking if it was used *before* forking.
		The problem is that the default asynchronous resolver uses the
		hub's threadpool, which is initialized the first time it is
		used. Some bug prevents the threadpool from working after fork
		(it seems that the on_fork listener is not being called; if it
		gets called things work). The app startup sequence invokes DNS
		and thus inits the thread pool, so the DNS operations that
		happen after the fork fail---inparticular, starting the server
		accesses DNS and so we never get to the point of listening on
		the socket. One workaround for this is to manually re-init the
		thread pool if needed; another is to use the Ares resolver.
		For now, I'm attempting to re-init the thread pool. (TODO:
		This may be platform specific?)
		"""
		# Patch up the thread pool and DNS if needed
		hub = gevent.hub.get_hub()
		if self.cfg.preload_app and hub._threadpool is not None and hub._threadpool._size: # same condition it uses
			hub._threadpool._on_fork()

		# The Dataserver reloads itself automatically in the preload scenario
		# based on the post_fork and IProcessDidFork listener

		self._load_legacy_app()


		# Tweak the max connections per process if it is at the default (1000)
		# Large numbers of HTTP connections means large numbers of
		# database connections; multiply that by the number of processes and number
		# of machines, and we quickly run out. We probably can't really handle
		# 1000 simultaneous connections anyway, even though we are non-blocking
		worker_connections = self.cfg.settings['worker_connections']
		if worker_connections.value == worker_connections.default and worker_connections.value >= self.PREFERRED_MAX_CONNECTIONS:
			worker_connections.set( self.PREFERRED_MAX_CONNECTIONS )
			self.worker_connections = self.PREFERRED_MAX_CONNECTIONS


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
		# Make 0.17 more like 0.16.1 (TODO: Needed anymore?)
		self.socket = self.sockets[0]

		if False: # pragma: no cover
			def print_stacks():
				from nti.appserver._util import dump_stacks
				import sys
				while True:
					gevent.sleep( 15.0 )
					print( '\n'.join( dump_stacks() ), file=sys.stderr )

			gevent.spawn( print_stacks )

		# Everything must be complete and ready to go before we call into
		# the super, it in turn calls run()
		# TODO: Errors here get silently swallowed and gunicorn just cycles the worker
		# (But at least as of 0.17.2 they are now reported? Check this.)
		if _call_super: # pragma: no cover
			super(GeventApplicationWorker,self).init_process()


class _ServerFactory(object):
	"""
	Given a worker that has already created the app server, does
	what's necessary to finish initializing it for running (such as
	messing with socket blocking and adjusting handler classes).
	Serves as the 'server_class' value.

	Also takes care of creating the flash policy server on its port instead
	of the application.

	"""

	def __init__( self, worker ):
		self.worker = worker


	def __call__( self,  listen_on_socket, application=None, spawn=None, log=None, handler_class=None):
		if listen_on_socket.cfg_addr[1] == self.worker.cfg.flash_policy_server_port: # Is this the flash port?
			logger.info( "Created FlashPolicyServer on %s", listen_on_socket )
			return FlashPolicyServer( listen_on_socket )

		app_server = WebSocketServer(
				listen_on_socket,
				application,
				handler_class=handler_class or GeventApplicationWorker.wsgi_handler)
		app_server.worker = self.worker # See _PyWSGIWebSocketHandler.get_environ # FIXME: Eliminate this

		# The worker will provide a Pool based on the
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
		app_server.set_spawn(spawn)
		# We want to log with the appropriate logger, which
		# has monitoring info attached to it
		app_server.log = log

		# Now, for logging to actually work, we need to replace
		# the handler class with one that sets up the required values in the
		# environment, as per ggevent.
		assert app_server.handler_class is _PyWSGIWebSocketHandler
		app_server.base_env = ggevent.PyWSGIServer.base_env
		return app_server

# Manage the forking events
from zope import interface
from zope import component
from zope.event import notify
from nti.processlifetime import IProcessWillFork, ProcessWillFork
from nti.processlifetime import ProcessDidFork

class _IGunicornWillFork(IProcessWillFork):
	"""
	An event specific to gunicorn forking.
	"""

	arbiter = interface.Attribute( "The master arbiter" )
	worker = interface.Attribute( "The new worker that will run in the child" )

class _IGunicornDidForkWillExec(interface.Interface):
	"""
	An event specific to gunicorn sigusr2 handling.
	"""
	arbiter = interface.Attribute( "The current master arbiter; will be going away" )

@interface.implementer(_IGunicornWillFork)
class _GunicornWillFork(ProcessWillFork):

	def __init__( self, arbiter, worker ):
		self.arbiter = arbiter
		self.worker = worker

@interface.implementer(_IGunicornDidForkWillExec)
class _GunicornDidForkWillExec(object):

	def __init__( self, arbiter ):
		self.arbiter = arbiter

@component.adapter(_IGunicornWillFork)
def _process_will_fork_listener( event ):
	from nti.dataserver import interfaces as nti_interfaces
	ds = component.queryUtility( nti_interfaces.IDataserver )
	if ds:
		# Close the ds in the master, we don't need those connections
		# sticking around here. It will be reopened in the child
		ds.close()

@component.adapter(_IGunicornDidForkWillExec)
def _process_did_fork_will_exec( event ):
	# First, kill the DS for good measure
	_process_will_fork_listener( event )
	# Now, run component cleanup, etc, for good measure
	from zope import site
	site = site
	from zope.testing import cleanup
	cleanup.cleanUp()

def _pre_fork( arbiter, worker ):
	notify( _GunicornWillFork( arbiter, worker ) )

def _post_fork( arbiter, worker ):
	notify( ProcessDidFork() )

def _pre_exec( arbiter ):
	# Called during sigusr2 handling from arbiter.reexec(),
	# just after forking (and in the child process)
	# but before exec'ing the new master
	notify( _GunicornDidForkWillExec( arbiter ) )

from gunicorn.app.pasterapp import PasterServerApplication
class _PasterServerApplication(PasterServerApplication):
	"""
	Exists to prevent loading of the app multiple times.
	"""

	def __init__( self, app, gcfg=None, host="127.0.0.1", port=None, *args, **kwargs):

		super(_PasterServerApplication, self).__init__( app, gcfg=gcfg, host=host, port=port, *args, **kwargs )
		self.cfg.set( 'pre_fork', _pre_fork )
		self.cfg.set( 'post_fork', _post_fork )
		self.cfg.set( 'pre_exec', _pre_exec )
		if self.cfg.pidfile is None:
			# Give us a pidfile in the $DATASERVER_DIR var directory
			import os
			ds_dir = os.environ.get( 'DATASERVER_DIR' )
			if ds_dir:
				pidfile = os.path.join( ds_dir, 'var', 'gunicorn.pid' )
				self.cfg.set( 'pidfile',  pidfile )

		assert len( self.cfg.bind ) == 1
		self._setup_flash_port( self.cfg, gcfg )

	@classmethod # for testing
	def _setup_flash_port( cls, cfg, global_conf ):
		# Setup the flash port, if configured.
		# An empty or missing value means to use the default port.
		# A positive integer means to use that port. A negative
		# integer disables the port.
		# We bind this in the standard fashion so that it survives properly across
		# fork/exec. It also simplifies things.
		cfg.flash_policy_server_port = FlashPolicyServer.NONPRIV_POLICY_PORT
		if global_conf and 'flash_policy_server_port' in global_conf and global_conf['flash_policy_server_port']:
			port = int(global_conf['flash_policy_server_port'])
			if port > 0:
				cfg.flash_policy_server_port = port
			else:
				cfg.flash_policy_server_port = None

		if cfg.flash_policy_server_port:
			cfg.set( 'bind', cfg.bind + [':' + str(cfg.flash_policy_server_port)] )


	def load(self):
		if self.app is None:
			self.app = loadwsgi.loadapp(self.cfgurl, name='dataserver_gunicorn', relative_to=self.relpath)
		return self.app


def paste_server_runner(app, gcfg=None, host="127.0.0.1", port=None, *args, **kwargs):
	"""
	A paster server entrypoint.

	See :func:`gunicorn.app.pasterapp.paste_server`.
	"""
	_PasterServerApplication(None, gcfg=gcfg, host=host, port=port, *args, **kwargs).run()
