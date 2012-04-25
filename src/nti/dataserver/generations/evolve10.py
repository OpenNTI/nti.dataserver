#!/usr/bin/env python
"""zope.generations generation 10 evolver for nti.dataserver
$Id$
"""
from __future__ import print_function, unicode_literals

__docformat__ = 'restructuredtext'

generation = 10

from zope.generations.utility import findObjectsMatching
from zope import minmax

from nti.dataserver import sessions, interfaces as nti_interfaces


def evolve( context ):
	"""
	Evolve generation 9 to generation 10 by changing the root session storage.
	"""
	conn = context.connection

	sess_conn = conn.get_connection( 'Sessions' )
	storage = sessions.SessionServiceStorage()
	sess_conn.add( storage )
	old_storage = sess_conn.root()['session_storage']
	storage.session_map = old_storage.session_map
	storage.session_index = old_storage.session_index
	sess_conn.root()['session_storage'] = storage

	lsm = conn.root()['nti.dataserver'].getSiteManager()
	lsm.registerUtility( storage, provided=nti_interfaces.ISessionServiceStorage )

	# FIXME: I don't understand why this is necessary. Why does
	# the PersistentOidResolver sometimes not have a _p_jar?
	rsv = lsm.getUtility( nti_interfaces.IOIDResolver )
	if rsv._p_jar is None:
		rsv._p_jar = conn
