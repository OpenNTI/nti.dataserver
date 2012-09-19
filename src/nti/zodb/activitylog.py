#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Logging of database connection activity. Activate this with ZCML::

	<include package="nti.zodb" file="configure_activitylog.zcml" />

Originally based on code from the unreleased zc.zodbactivitylog.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

class ActivityMonitor(object):
	"""
	ZODB database activity monitor that logs connection transfer information.
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
		logger.debug( "closedConnection=%s", {'loads': loads, 'stores': stores, 'database': db_name } )

	def __getattr__(self, name):
		return getattr(self._base, name)

def register_subscriber( event ):
	"""
	Subscriber to the :class:`zope.processlifetime.IDatabaseOpenedEvent`
	that registers an activity monitor.
	"""

	for database in event.database.databases.values():
		database.setActivityMonitor( ActivityMonitor( database.getActivityMonitor() ) )
