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

__old__ = __name__ # Force absolute import for gunicorn, since we shadow its name
__name__ = '__main__' # Note that we cannot do this and use from __future__ imports
import gunicorn.workers.ggevent as ggevent
import gunicorn.http.wsgi as wsgi
__name__ = __old__

import gevent
import gevent.socket
import logging
logger = logging.getLogger(__name__)

import sys
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


class GeventApplicationWorker(ggevent.GeventPyWSGIWorker):

	app_server = None
	app = None
	server_class = None
	socket = None

	@classmethod
	def setup(cls):
		"""
		We cannot patch the entire system to work with gevent due to issues
		with ZODB (but see application.py)
		Instead, we patch just our socket when we create it.
		"""
		pass


	def init_process(self):
		"""
		We must create the appserver only once, and only after the process
		has forked. Doing it before the fork leads to thread-related problems
		and a deadlock (the ZEO connection pthreads do not survive the fork, I think).
		"""
		gevent.hub.get_hub() # init the hub
		dummy_app = self.app.app
		wsgi_app = loadwsgi.loadapp( 'config:' + dummy_app.global_conf['__file__'], name='dataserver_gunicorn' )
		self.app_server = nti.appserver.standalone._create_app_server( wsgi_app,
																	   dummy_app.global_conf,
																	   port=dummy_app.global_conf['http_port'],
																	   **dummy_app.kwargs )

		def factory(*args,**kwargs):
			# The super class will provide a Pool based on the
			# worker_connections setting
			self.app_server.set_spawn(kwargs['spawn'])
			# We want to log with the appropriate logger, which
			# has monitoring info attached to it
			self.app_server.log = kwargs['log']
			#self.app_server.handler_class.log_request = l_r
			# The super class will set the socket to blocking because
			# it thinks it has monkey patched the system. It hasn't.
			# Therefore the socket must be non-blocking or we get
			# the dreaded 'cannot switch to MAINLOOP from MAINLOOP'
			# (Non blocking is how gevent's baseserver:_tcp_listener sets things up)
			self.app_server.socket.setblocking(0)
			# Now, for logging to actually work, we need to replace
			# the handler class with one that sets up the required values in the
			# environment, as per ggevent.
			worker = self
			class PhonyRequest(object):
				pass
			class HandlerClass(self.app_server.handler_class,ggevent.PyWSGIHandler):

				def log_request(self):
					ggevent.PyWSGIHandler.log_request( self )
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
						path, query = req.uri.split('?', 1)
					else:
						path, query = req.uri, ''
					req.query = query
					req.headers = getattr( req, 'headers', None ) or req.get_input_headers()
					rsp, env = wsgi.create(req, self.socket, self.client_address, worker.address, worker.cfg)
					return env
				def get_environ(self):
					if not getattr( self, 'request', None ):
						self.request = PhonyRequest()
						self.request.input_buffer = None
						self.request.typestr = self.command
						self.request.uri = self.path
						self.request.headers = []
						self.request.path = self.path
						for header in self.headers.headers:
							k, v = header.split( ':', 1)
							self.request.headers.append( (k.upper(), v.strip()) )

						self.request.version = (1,0)
					env = self.prepare_env()
					# This does everything except it screws with REMOTE_ADDR
					# and some other values we want gunicorn to rule
					ws_env = super(HandlerClass,self).get_environ()
					for k in ('RAW_URI', 'wsgi.errors', 'wsgi.file_wrapper',
							  'REMOTE_ADDR','SERVER_SOFTWARE',
							  'SERVER_NAME', 'SERVER_PORT',
							  'wsgi.url_scheme'):
						ws_env[k] = env[k]
					ws_env['gunicorn.sock'] = self.socket
					ws_env['gunicorn.socket'] = self.socket
					return ws_env
			self.app_server.handler_class = HandlerClass
			self.app_server.base_env = ggevent.PyWSGIServer.base_env
			return self.app_server

		self.server_class = factory
		self.socket = gevent.socket.socket(_sock=self.socket)
		self.app_server.socket = self.socket
		# Everything must be complete and ready to go before we call into
		# the super, it in turn calls run()
		super(GeventApplicationWorker,self).init_process()
