from __future__ import print_function, unicode_literals

generation = 11

from nti.dataserver import interfaces as nti_interfaces

from nti.contentsearch import create_repoze_datastore
from nti.contentsearch.interfaces import IRepozeDataStore

def evolve(context):
	"""
	Evolve generation 10 to generation 11 by recreating the repoze store
	"""
	conn = context.connection
	root = conn.root()

	search_conn = conn.get_connection( 'Search' )
	search_conn.root().pop('repoze_datastore', None)
	
	container = root['nti.dataserver']
	lsm = container.getSiteManager()

	# create a new store and set it
	repoze_datastore = create_repoze_datastore()
	search_conn.add(repoze_datastore)
	search_conn.root()['repoze_datastore'] = repoze_datastore
	
	lsm.registerUtility(repoze_datastore, provided=IRepozeDataStore)
	rsv = lsm.getUtility( nti_interfaces.IOIDResolver )
	if rsv._p_jar is None:
		rsv._p_jar = conn
