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

import codecs

from nti.dataserver import interfaces as nti_interfaces
from zope import component

from .application import createApplication
from .application_server import WebSocketServer
from paste.deploy.converters import asbool

SOCKET_IO_PATH = 'socket.io'

_marker = object()

_ZCML_LIBRARY_TEMPLATE = """
<configure xmlns="http://namespaces.zope.org/zope"
		   xmlns:zcml="http://namespaces.zope.org/zcml"
		   xmlns:lib="http://nextthought.com/ntp/contentlibrary"
		   i18n_domain='nti.dataserver'>

	<include package="zope.component" />
	<include package="nti.contentlibrary" file="meta.zcml" />

	%s

</configure>
"""

def configure_app( global_config,
				   deploy_root=_marker,
				   nti_create_ds=True,
				   sync_changes=True,
				   **settings ):
	":return: A WSGI callable."

	if '__file__' in global_config and '__file__' not in settings:
		settings['__file__'] = global_config['__file__']

	if deploy_root is not _marker:
		# Temporary code. Remove after May 2013
		logger.warn( "deploy_root and s3_cdn_cname are deprecated. Please move to a ZCML file. " )

		zcml_path = settings.get( 'library_zcml' ) or os.path.join( os.getenv( 'DATASERVER_DIR' ), 'etc', 'library.zcml' )
		if not os.path.exists( zcml_path ):
			logger.warn( "Copying existing deploy root to zcml file %s", zcml_path )

			# Quick hack to switch on or off the library: if the root is a path
			# then we use a filesystem view. If it's not, then we assume it must be a bucket.
			# TODO: This needs to change because it breaks the glossary/dictionary, which
			# is assumed to be in the deploy_root?
			if '/' in deploy_root:
				lib_str = '<lib:filesystemLibrary directory="%s" />' % deploy_root
			elif 's3_cdn_cname' in settings and settings['s3_cdn_cname']:
				lib_str = '<lib:s3Library bucket="%s" cdn_name="%s" />' % (deploy_root, settings['s3_cdn_cname'])
			else:
				lib_str = '<lib:s3Library bucket="%s" />' % deploy_root

			with codecs.open(zcml_path, 'w', encoding='utf-8') as f:
				f.write( _ZCML_LIBRARY_TEMPLATE % lib_str )

	application = createApplication( int(settings.get('http_port','8081')),
									 library=None,
									 process_args=True,
									 create_ds=nti_create_ds,
									 sync_changes=asbool(sync_changes),
									 **settings)

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
	httpd = WebSocketServer(
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
