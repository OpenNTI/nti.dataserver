#!/usr/bin/env python
"""zope.generations generation 9 evolver for nti.dataserver
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
	Evolve generation 8 to generation 9 by renaming the heartbeat property of sessions.
	"""
	session = None
	for session in findObjectsMatching( context.connection.get_connection( 'Sessions' ).root(), nti_interfaces.ISocketSession.providedBy ):
		session._last_heartbeat_time = session.__dict__['last_heartbeat_time']
		del session.__dict__['last_heartbeat_time']
