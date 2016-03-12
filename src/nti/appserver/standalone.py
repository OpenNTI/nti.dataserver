#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import platform

from zope import component

from paste.deploy.converters import asbool

from nti.appserver.application import createApplication
from nti.appserver.application_server import WebSocketServer

from nti.dataserver import interfaces as nti_interfaces

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

def configure_app(global_config,
				  nti_create_ds=True,
				  sync_changes=True,
				  **settings):
	"""
	:return: A WSGI callable.
	"""

	if '__file__' in global_config and '__file__' not in settings:
		settings['__file__'] = global_config['__file__']

	if 'deploy_root' in settings:
		# Old code, shouldn't be around anymore
		raise TypeError("deploy_root and s3_cdn_cname are deprecated. Please move to a ZCML file. ")

	try:
		__traceback_info__ = global_config, settings
		application = createApplication(int(settings.get('http_port', '8081')),
										process_args=True,
										create_ds=nti_create_ds,
										sync_changes=asbool(sync_changes),
										**settings)
	except:
		logger.exception("Failed to create application")
		raise

	return application

def _serve(httpd):
	while True:
		try:
			# SIGHUP could cause this to raise 'interrupted system call'
			httpd.serve_forever()
		except KeyboardInterrupt:
			component.getUtility(nti_interfaces.IDataserver).close()
			raise

def _create_app_server(wsgi_app, global_conf, host='', port=None, **kwargs):
	httpd = WebSocketServer(
		(host, int(port)),
		wsgi_app)
	return httpd

# The paste.server_runner, only good with pyramid_main
def server_runner(wsgi_app, global_conf, host='', port=None, **kwargs):
	# Temp hack for compatibility with code that wants to use the environment
	# variable to control the HTTP_PORT: if the arg is the default but env var isn't,
	# use the env var
	httpd = _create_app_server(wsgi_app, global_conf, host, port, **kwargs)
	logger.info("Starting server %s:%s %s", platform.uname()[1], port, httpd.__class__)
	_serve(httpd)
