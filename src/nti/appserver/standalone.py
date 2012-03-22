#!/usr/bin/env python2.7

import logging
logger = logging.getLogger( __name__ )


import os
import platform

from nti.dataserver.library import DynamicLibrary
from nti.dataserver import interfaces as nti_interfaces
from zope import component


from application import createApplication, AppServer
from paste.deploy.converters import asbool


SOCKET_IO_PATH = 'socket.io'
#USE_FILE_INDICES = 'USE_ZEO_USER_INDICES' not in os.environ
#HTTP_PORT = int(os.environ.get('DATASERVER_PORT', '8081'))
#SYN_CHANGES = 'DATASERVER_SYNC_CHANGES' in os.environ

def configure_app( global_config,
				   deploy_root='/Library/WebServer/Documents/',
				   nti_create_ds=True,
				   sync_changes=True,
				   **settings ):
	":return: A WSGI callable."

	# We'll volunteer to serve all the files in the root directory
	# Note that this is not dynamic (the library is)
	# but in production we expect to have static files served by
	# nginx/apache
	serveFiles = [ ('/' + s, os.path.join( deploy_root, s) )
				   for s in os.listdir( deploy_root )
				   if os.path.isdir( os.path.join( deploy_root, s ) )]


	application,main = createApplication( int(settings.get('http_port','8081')),
										  DynamicLibrary( deploy_root ),
										  process_args=True,
										  create_ds=nti_create_ds,
										  sync_changes=asbool(sync_changes),
										  **settings)

	main.setServeFiles( serveFiles )
	return application

def _serve(httpd):
	while True:
		try:
			#SIGHUP could cause this to raise 'interrupted system call'
			httpd.serve_forever()
		except KeyboardInterrupt:
			component.getUtility(nti_interfaces.IDataserver).close()
			raise

def _create_app_server(wsgi_app, global_conf, host='', port=None, **kwargs):
	httpd = AppServer(
		(host, int(port)),
		wsgi_app,
		policy_server=False,
		namespace=SOCKET_IO_PATH,
		session_manager = component.getUtility(nti_interfaces.IDataserver).session_manager )
	return httpd

# The paste.server_runner, only good with pyramid_main
def server_runner(wsgi_app, global_conf, host='', port=None, **kwargs):
	# Temp hack for compatibility with code that wants to use the environment
	# variable to control the HTTP_PORT: if the arg is the default but env var isn't,
	# use the env var
	httpd = _create_app_server(wsgi_app, global_conf, host, port, **kwargs)
	logger.info( "Starting server %s:%s %s", platform.uname()[1], port, httpd.__class__ )
	_serve( httpd )
