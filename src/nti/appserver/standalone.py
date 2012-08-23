#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import platform

import boto

from nti.contentlibrary.filesystem import DynamicLibrary
from nti.contentlibrary.boto_s3 import BotoS3BucketContentLibrary
from nti.contentlibrary.externalization import map_all_buckets_to
from nti.dataserver import interfaces as nti_interfaces
from zope import component

from .application import createApplication, AppServer
from paste.deploy.converters import asbool

SOCKET_IO_PATH = 'socket.io'

def configure_app( global_config,
				   deploy_root='/Library/WebServer/Documents/',
				   nti_create_ds=True,
				   sync_changes=True,
				   **settings ):
	":return: A WSGI callable."

	# Quick hack to switch on or off the library: if the root is a path
	# then we use a filesystem view. If it's not, then we assume it must be a bucket.
	# TODO: This needs to change because it breaks the glossary/dictionary, which
	# is assumed to be in the deploy_root?
	if '/' in deploy_root:
		library = DynamicLibrary( deploy_root )
		# We'll volunteer to serve all the files in the root directory
		# Note that this is not dynamic (the library is)
		# but in production we expect to have static files served by
		# nginx/apache
		serveFiles = [ ('/' + s, os.path.join( deploy_root, s) )
					   for s in os.listdir( deploy_root )
					   if os.path.isdir( os.path.join( deploy_root, s ) )]
	else:
		serveFiles = ()
		boto_bucket = boto.connect_s3().get_bucket( deploy_root )
		library = BotoS3BucketContentLibrary( boto_bucket )


	application,main = createApplication( int(settings.get('http_port','8081')),
										  library,
										  process_args=True,
										  create_ds=nti_create_ds,
										  sync_changes=asbool(sync_changes),
										  **settings)

	main.setServeFiles( serveFiles )

	# If we are serving content from a bucket, we might have a CDN on top of it
	# in the case that we are also serving the application. Rewrite bucket
	# rules with that in mind, replacing the HTTP Host: and Origin: aware stuff
	# we would do if we were serving the application and content both from a cdn.
	if 's3_cdn_cname' in settings and settings['s3_cdn_cname']:
		map_all_buckets_to( settings['s3_cdn_cname'] )

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
		wsgi_app )
	return httpd

# The paste.server_runner, only good with pyramid_main
def server_runner(wsgi_app, global_conf, host='', port=None, **kwargs):
	# Temp hack for compatibility with code that wants to use the environment
	# variable to control the HTTP_PORT: if the arg is the default but env var isn't,
	# use the env var
	httpd = _create_app_server(wsgi_app, global_conf, host, port, **kwargs)
	logger.info( "Starting server %s:%s %s", platform.uname()[1], port, httpd.__class__ )
	_serve( httpd )
