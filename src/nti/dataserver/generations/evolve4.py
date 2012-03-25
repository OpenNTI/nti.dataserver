#!/usr/bin/env python
"""zope.generations generation 4 evolver for nti.dataserver
$Id$
"""
from __future__ import print_function, unicode_literals

__docformat__ = 'restructuredtext'

generation = 4

from zope.site import LocalSiteManager, SiteManagerContainer

from nti.dataserver import _Dataserver, interfaces as nti_interfaces
from persistent.list import PersistentList

def evolve( context ):
	"""
	Evolve generation 3 to generation 4 by moving everything into a site
	"""
	conn = context.connection
	root = conn.root()

	container = SiteManagerContainer()
	lsm = LocalSiteManager( None, default_folder=None ) # No parent
	container.setSiteManager( lsm )

	for key in ('users', 'vendors', 'library', 'quizzes', 'providers' ):
		lsm[key] = root['key']
		lsm[key].__name__ = key
		try:
			del root['key']
		except KeyError: pass

	# We drop the old changes
	if not lsm.has_key( 'changes'):
		lsm['changes'] = PersistentList()

	root['nti.dataserver'] = container
	oid_resolver =  _Dataserver.PersistentOidResolver()
	conn.add( oid_resolver )
	lsm.registerUtility( oid_resolver, provided=nti_interfaces.IOIDResolver )
