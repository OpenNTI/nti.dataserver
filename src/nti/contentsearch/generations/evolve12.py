from __future__ import print_function, unicode_literals

generation = 12

import zope.intid

from evolve10 import reindex

def evolve(context):
	"""
	Evolve generation 11 to generation 12by reindexing all
	"""
	conn = context.connection
	root = conn.root()

	search_conn = conn.get_connection( 'Search' )
	repoze_datastore = search_conn.root()['repoze_datastore']
	
	container = root['nti.dataserver']
	lsm = container.getSiteManager()
	connection = getattr( lsm, '_p_jar', None )

	ds_intid = lsm.getUtility( provided=zope.intid.IIntIds )
	for user in context.connection.root()['nti.dataserver']['users'].values():
		reindex(connection, repoze_datastore, user, ds_intid, True)