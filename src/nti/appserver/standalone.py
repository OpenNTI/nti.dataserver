#!/usr/bin/env python2.7

import logging
logger = logging.getLogger( __name__ )


import os
import platform

from nti.dataserver.library import Library
from nti.dataserver import interfaces as nti_interfaces
from zope import component


from application import createApplication, AppServer


SOCKET_IO_PATH = 'socket.io'
#USE_FILE_INDICES = 'USE_ZEO_USER_INDICES' not in os.environ
#HTTP_PORT = int(os.environ.get('DATASERVER_PORT', '8081'))
#SYNC_CHANGES = 'DATASERVER_SYNC_CHANGES' in os.environ

def configure_app( global_config,
				   deploy_root='/Library/WebServer/Documents/',
				   nti_create_ds=True,
				   sync_changes=True,
				   **settings ):
	":return: A WSGI callable."

#	os.environ['DATASERVER_NO_REDIRECT'] = '1'


	root = deploy_root
	# We'll volunteer to serve all the files in the root directory
	# This SHOULD include 'prealgebra' and 'mathcounts'
	serveFiles = [ ('/' + s, os.path.join( root, s) )
				   for s in os.listdir( root )
				   if os.path.isdir( os.path.join( root, s ) )]
	libraryPaths = []
	for _, path in serveFiles:
		to_append = None
		if path.endswith( '/prealgebra' ):
			to_append = (path, False, 'Prealgebra', '/prealgebra/icons/chapters/PreAlgebra-cov-icon.png')
		elif path.endswith( '/mathcounts' ):
			to_append = (path, False, 'MathCounts', '/mathcounts/icons/mathcounts-logo.gif' )
		else:
			to_append = (path, False)
		libraryPaths.append( to_append )

	application,main = createApplication( int(settings.get('http_port','8081')),
										  Library( libraryPaths ),
										  process_args=True,
										  create_ds=nti_create_ds,
										  sync_changes=bool(sync_changes),
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


# The paste.server_runner, only good with pyramid_main
def server_runner(wsgi_app, global_conf, host='', port=None, **kwargs):
	# Temp hack for compatibility with code that wants to use the environment
	# variable to control the HTTP_PORT: if the arg is the default but env var isn't,
	# use the env var
	httpd = AppServer(
		(host, int(port)),
		wsgi_app,
		policy_server=False,
		namespace=SOCKET_IO_PATH,
		session_manager = component.getUtility(nti_interfaces.IDataserver).session_manager )
	logger.info( "Starting server %s:%s %s", platform.uname()[1], port, httpd.__class__ )
	_serve( httpd )
