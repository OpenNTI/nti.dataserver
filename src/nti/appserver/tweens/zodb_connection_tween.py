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

import gc
import os
from pprint import pprint
from cStringIO import StringIO

import transaction

class zodb_connection_tween(object):
	"""
	Opens and closes a connection, after first putting the
	local transaction manager into explicit mode.

	Set up the connection tween. You must have `nti_zodb_root_db`
	established on the registry.

	"""

	DEBUG_OFF = True
	DEBUG_COUNT = 100

	def __init__(self, handler, registry):
		self.handler = handler
		self._count = 0

	def __call__(self, request):
		# logger.debug("Connection details %s", '\n'.join([str(x) for x in request.registry.nti_zodb_root_db.connectionDebugInfo()]))
		# The value of nti_zodb_root_db may change at runtime,
		# so we don't cache it (only during tests).

		# Having the transaction manager be in explicit mode
		# *before* we open the connection lets it make certain
		# optimizations. The transaction tween below us will also
		# do this, but by then its too late. We never bother to
		# reset this, we're in a new greenlet and this is greenlet-local.
		transaction.manager.explicit = True

		request.nti_zodb_root_connection = request.registry.nti_zodb_root_db.open()
		assert request.nti_zodb_root_connection.explicit_transactions
		self._debug_connection(request)
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

	def _debug_connection(self, request):
		conn = request.nti_zodb_root_connection
		for c in conn.connections.values():
			c.setDebugInfo(request.path_url)
		if self.DEBUG_OFF:
			return

		self._count += 1
		if self._count < self.DEBUG_COUNT:
			return
		self._count = 0

		db = conn.db()
		pid = os.getpid()

		stream = StringIO()
		infos = {}
		need_gc = []
		for name, db in db.databases.items():
			db._a()
			try:
				infos[name] = sorted(db.connectionDebugInfo(), key=lambda x: x['info'])
				infos[name + ' LEN'] = len(infos[name])
				infos[name + ' AVA'] = len(db.pool.available)
				if len(infos[name]) > db.pool.size:
					need_gc.append((name, db, len(infos[name])))
			finally:
				db._r()
		pprint(infos, stream)
		logger.debug("Connection details in pid %s:\n%s", pid, stream.getvalue())
		if need_gc:
			logger.warn("Too many connection objects in pid %s: %s", pid, need_gc)

			def _print_refs(c):
				if c in c.db().pool.available:
					return
				stream = StringIO()
				objs = gc.get_referrers(c)
				by_type = {}
				details = []
				for o in objs:
					if getattr(o, '_p_jar', None) is c:
						# Filter out things that are directly tied to it
						continue
					by_type[type(o)] = by_type.get(type(o), 0) + 1
					if type(o) is list and o is not objs and o is not details:
						details.append(o)
						oo = gc.get_referrers(o)
						details.append({type(x) for x in oo if x is not objs and x is not details})
						for x in oo:
							if isinstance(x, dict):
								details.append(x.keys())
				pprint(by_type, stream)
				logger.warn("Referrers to %s:\n%s", c, stream.getvalue())
				if details:
					stream = StringIO()
					pprint(details, stream)
					logger.warn("Details for %s:\n%s", c, stream.getvalue())

			for name, db, _ in need_gc:
				db._a()
				try:
					for conn in db.pool:
						_print_refs(conn)
				finally:
					db._r()

zodb_connection_tween_factory = zodb_connection_tween
