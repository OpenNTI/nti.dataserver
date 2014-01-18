#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A simpler version of :mod:`pyramid_zodbconn` that only provides access
to a single database.

This database is found in the `nti_zodb_root_db` attribute of the Pyramid
registry. You are responsible for setting this up before calling the
tween factory. After this tween runs, there will be a new attribute on the
request, `nti_zodb_root_connection`. If you have already closed this connection,
you may delete this attribute.

This must be installed *above* the transaction tween.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

class zodb_connection_tween(object):
	"""
	Opens and closes a connection.

	Set up the connection tween. You must have `nti_zodb_root_db`
	established on the registry.

	"""

	__slots__ = ('handler')

	def __init__(self, handler, registry):
		self.handler = handler

	def __call__(self, request):
		#logger.debug("Connection details %s", '\n'.join([str(x) for x in request.registry.nti_zodb_root_db.connectionDebugInfo()]))
		# The value of nti_zodb_root_db may change at runtime,
		# so we don't cache it (only during tests)
		request.nti_zodb_root_connection = request.registry.nti_zodb_root_db.open()
		try:
			return self.handler(request)
		finally:
			try:
				conn = request.nti_zodb_root_connection
			except AttributeError:
				pass
			else:
				try:
					conn.close()
				finally:
					del request.nti_zodb_root_connection

zodb_connection_tween_factory = zodb_connection_tween
