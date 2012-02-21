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

__old_name__ = __name__
__name__ = '__main__' # Force absolute import for gunicorn
import gunicorn.workers.ggevent as ggevent
import gevent
import gevent.socket
__name__ = __old_name__


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

		def l_r(self):
			c = self.__class__
			self.__class__ = ggevent.PyWSGIHandler
			ggevent.PyWSGIHandler.log_request( self )
			self.__class__ = c
		def factory(*args,**kwargs):
			# The super class will provide a Pool based on the
			# worker_connections setting
			self.app_server.set_spawn(kwargs['spawn'])
			# We want to log with the appropriate logger, which
			# has monitoring info attached to it
			self.app_server.log = kwargs['log']
			self.app_server.handler_class.log_request = l_r
			# The super class will set the socket to blocking because
			# it thinks it has monkey patched the system. It hasn't.
			# Therefore the socket must be non-blocking or we get
			# the dreaded 'cannot switch to MAINLOOP from MAINLOOP'
			# (Non blocking is how gevent's baseserver:_tcp_listener sets things up)
			self.app_server.socket.setblocking(0)
			return self.app_server
		self.server_class = factory
		self.socket = gevent.socket.socket(_sock=self.socket)
		self.app_server.socket = self.socket
		# Everything must be complete and ready to go before we call into
		# the super, it in turn calls run()
		super(GeventApplicationWorker,self).init_process()
