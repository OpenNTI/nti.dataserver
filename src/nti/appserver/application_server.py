#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Implementations of network servers.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import gevent.pywsgi
import gevent.server

import geventwebsocket.handler

class WebSocketServer(gevent.pywsgi.WSGIServer): # In gevent 1.0, gevent.wsgi is an alias for WSGIServer
	"""
	HTTP server that can handle websockets.
	"""

	handler_class = geventwebsocket.handler.WebSocketHandler
	def __init__( self, *args, **kwargs ):
		"""
		:raises ValueError: If a ``handler_class`` keyword argument is supplied
			that specifies a non-:class:`geventwebsocket.handler.WebSocketHandler` subclass.
			That type of handler is required for websockets to work.
		"""
		super(WebSocketServer,self).__init__(*args, **kwargs)
		if not issubclass( self.handler_class, geventwebsocket.handler.WebSocketHandler ):
			raise ValueError( "Unable to run with a handler that is not a type of %s", WebSocketServer.handler_class )


class FlashPolicyServer(gevent.server.StreamServer):
	"""
	TCP Server for `Flash policies <http://www.adobe.com/devnet/flashplayer/articles/socket_policy_files.html>`_
	"""


	policy = b"""<?xml version="1.0" encoding="utf-8"?>
	<!DOCTYPE cross-domain-policy SYSTEM "http://www.macromedia.com/xml/dtds/cross-domain-policy.dtd">
	<cross-domain-policy>
		<allow-access-from domain="*" to-ports="*"/>
	</cross-domain-policy>\n"""

	def __init__(self, listener=None, backlog=None):
		if listener is None:
			listener = ('0.0.0.0', 10843)
		super(FlashPolicyServer,self).__init__(listener=listener, backlog=backlog)

	def handle(self, socket, address):
		socket.sendall(self.policy)
