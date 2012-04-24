from __future__ import print_function, unicode_literals

__docformat__ = 'restructuredtext'

generation = 8

from nti.dataserver import interfaces as nti_interfaces

from nti.contentsearch import create_repoze_datastore
from nti.contentsearch.interfaces import IRepozeDataStore

import logging
logger = logging.getLogger( __name__ )

def evolve( context ):
	"""
	Evolve generation 7 to generation 8 by changing the root repoze catalog storage.
	"""
	conn = context.connection
	root = conn.root()

	search_conn = conn.get_connection( 'Search' )
	old_rds = search_conn.root()['repoze_datastore']
	
	container = root['nti.dataserver']
	lsm = container.getSiteManager()
	
	repoze_datastore = create_repoze_datastore()
	repoze_datastore.users.update(old_rds.users)
	repoze_datastore.docmaps.update(old_rds.docmaps)
	
	lsm.registerUtility(repoze_datastore, provided=IRepozeDataStore)

	rsv = lsm.getUtility( nti_interfaces.IOIDResolver )
	if rsv._p_jar is None:
		rsv._p_jar = conn