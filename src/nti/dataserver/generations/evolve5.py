#!/usr/bin/env python
"""zope.generations generation 4 evolver for nti.dataserver
$Id$
"""
from __future__ import print_function, unicode_literals

__docformat__ = 'restructuredtext'

generation = 5

from zope.site import LocalSiteManager, SiteManagerContainer

from nti.dataserver import sessions, interfaces as nti_interfaces


def evolve( context ):
	"""
	Evolve generation 4 to generation 5 by adding session storage.
	"""
	conn = context.connection
	root = conn.root()

	container = root['nti.dataserver']
	lsm = container.getSiteManager()

	sess_conn = conn.get_connection( 'Sessions' )
	storage = sessions.PersistentSessionServiceStorage()
	sess_conn.add( storage )
	sess_conn.root()['session_storage'] = storage
	lsm.registerUtility( storage, provided=nti_interfaces.ISessionServiceStorage )

	# FIXME: I don't understand why this is necessary. Why does
	# the PersistentOidResolver sometimes not have a _p_jar?
	rsv = lsm.getUtility( nti_interfaces.IOIDResolver )
	if rsv._p_jar is None:
		rsv._p_jar = conn
