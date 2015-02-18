#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Logging of database connection activity. Activate this with ZCML::

	<include package="nti.zodb" file="configure_activitylog.zcml" />

Originally based on code from the unreleased zc.zodbactivitylog.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

class _AbstractActivityMonitor(object):
	"""
	Base monitor for dealing correctly with chains.
	"""
	_base = None

	def __init__(self, base=None):
		if base:
			self._base = base

	def closedConnection(self, conn):
		loads, stores = conn.getTransferCounts(False)
		db_name = conn.db().database_name
		if self._base is not None:
			self._base.closedConnection(conn)
		conn.getTransferCounts(True) # Make sure connection counts are cleared
		self._closedConnection( loads, stores, db_name )

	def _closedConnection( self, loads, stores, db_name ):
		raise NotImplementedError()

	def __getattr__(self, name):
		return getattr(self._base, name)

class LogActivityMonitor(_AbstractActivityMonitor):
	"""
	ZODB database activity monitor that logs connection transfer information.
	"""

	def _closedConnection(self, loads, stores, db_name ):
		logger.debug( "closedConnection={'loads': %5d, 'stores': %5d, 'database': %s}",
					  loads, stores, db_name )

try:
	from perfmetrics import statsd_client
except ImportError:
	statsd_client = lambda *args, **kwargs:None

class StatsdActivityMonitor(_AbstractActivityMonitor):
	"""
	ZODB database activity monitor that stores counters in statsd. Experimental.
	"""

	def _closedConnection( self, loads, stores, db_name ):
		statsd = statsd_client()
		if statsd is None:
			return

		# Should these be counters or gauges? Or even sets?
		# counters are aggregated across all instances, gauges (by default) are broken out
		# by host
		buf = []
		statsd.gauge( 'ZODB.DB.' + db_name + '.loads',   loads, buf=buf )
		statsd.gauge( 'ZODB.DB.' + db_name + '.stores', stores, buf=buf )
		statsd.sendbuf( buf )

def register_subscriber( event ):
	"""
	Subscriber to the :class:`zope.processlifetime.IDatabaseOpenedWithRoot`
	that registers an activity monitor.
	"""
	# IDatabaseOpened fires for each database, so if we sub to that we'd do this many times.
	# WithRoot fires only once.
	for database in event.database.databases.values():
		dam = database.getActivityMonitor()
		database.setActivityMonitor( StatsdActivityMonitor(LogActivityMonitor(dam)))
