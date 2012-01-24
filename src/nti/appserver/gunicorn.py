#!/usr/bin/env python2.7
"""
Support for running the application with gunicorn. You must use our worker:

	gunicorn -k nti.appserver.gunicorn.GeventApplicationWorker nti.appserver.gunicorn:app -b 127.0.0.1:8081
"""
### XXX: This module has side-effects during import.
### In order to work with gunicorn, we must configure the application
### and create a variable for it.

__old_name__ = __name__
__name__ = '__main__' # Force absolute import for gunicorn
import gunicorn.workers.sync as sync
import gunicorn.workers.ggevent as ggevent
import gunicorn.util as util
import gevent
import gevent.socket
__name__ = __old_name__


import logging
if __name__ == '__main__':
	logging.basicConfig( level=logging.WARN )
	logging.getLogger( 'nti' ).setLevel( logging.DEBUG )


import nti.appserver.standalone

def app(*args):
	"""
	A dummy app variable.
	"""
	raise NotImplementedError( "Not a real app; specify the GeventApplicationWorker" )


class GeventApplicationWorker(ggevent.GeventPyWSGIWorker):

	app_server = None

	@classmethod
	def setup(cls):
		"""
		We cannot patch the entice system to work with gevent.
		Instead, we patch just our socket.
		"""
		pass


	def init_process(self):
		"""
		We must create the appserver only once, and only after the process
		has forked. Doing it before the fork leads to thread-related problems
		and a deadlock (the ZEO connection pthreads do not survive the fork, I think).
		"""
		gevent.hub.get_hub() # init the hub
		self.app_server = nti.appserver.standalone.configure_app(create_ds=True)
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
