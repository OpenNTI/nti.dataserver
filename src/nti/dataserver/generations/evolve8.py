#!/usr/bin/env python
"""zope.generations generation 8 evolver for nti.dataserver
$Id$
"""
from __future__ import print_function, unicode_literals

__docformat__ = 'restructuredtext'

generation = 8

from zope.generations.utility import findObjectsMatching
from zope import minmax

from nti.dataserver import datastructures, interfaces as nti_interfaces


def evolve( context ):
	"""
	Evolve generation 7 to generation 8 by changing all users to use Maximum and Merging
	for lastLoginTime and notificationCount, and similar for all sessions.
	"""
	for user in findObjectsMatching( context.connection.root()['nti.dataserver'].getSiteManager(), nti_interfaces.IUser.providedBy ):
		user.lastLoginTime = minmax.Maximum( user.lastLoginTime )
		user.notificationCount = datastructures.MergingCounter( user.notificationCount )

	session = None
	for session in findObjectsMatching( context.connection.get_connection( 'Sessions' ).root(), nti_interfaces.ISocketSession.providedBy ):
		session.heartbeats = datastructures.MergingCounter( session.heartbeats )
		session.hits = datastructures.MergingCounter( session.hits )
		session.last_heartbeat_time = minmax.Maximum( session.last_heartbeat_time )
