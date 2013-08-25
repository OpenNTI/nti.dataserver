#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Simple ping paste filter that does nothing but return a 200.

$Id$
"""
from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

class PingHandler(object):
	"""
	Handles the ``/_ops/ping`` url exactly.
	"""
	def __init__(self, app):
		self.captured = app

	def __call__(self, environ, start_response):
		__traceback_info__ = environ, start_response
		if environ['PATH_INFO'] == b'/_ops/ping':
			start_response( b'200 OK', [(b'Content-Type', b'text/plain')] )
			result = (b"",)
		else:
			try:
				result = self.captured(environ, start_response)
			except:
				logger.exception("Error during ping. Handler (%s)" % getattr(self.captured, "handle_request", None))
				raise
		return result

def ping_handler_factory(app, global_conf=None):
	"Paste factory for :class:`PingHandler`"
	return PingHandler(app)
