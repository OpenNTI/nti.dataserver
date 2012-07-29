from __future__ import print_function, unicode_literals

__docformat__ = 'restructuredtext'

generation = 10

import zope.intid
from ZODB.POSException import POSKeyError
from zope.generations.utility import findObjectsProviding

from nti.dataserver import interfaces as nti_interfaces

from nti.contentsearch.common import get_type_name
from nti.contentsearch import create_repoze_datastore
from nti.contentsearch.interfaces import IRepozeDataStore
from nti.contentsearch.common import indexable_type_names
from nti.contentsearch._repoze_index import create_catalog

import logging
logger = logging.getLogger( __name__ )

def _reindex(ds_conn, rds, user, ds_intid):
	username = user.username
	logger.debug('Reindexing object(s) for user %s' % username)

	# recreate catalogs
	for type_name in indexable_type_names:
		catalog = create_catalog(type_name)
		rds.add_catalog(username, catalog, type_name)

	counter = 0
	for obj in findObjectsProviding( user, nti_interfaces.IModeledContent):
		type_name = get_type_name(obj)
		if type_name and type_name in indexable_type_names:
			catalog = rds.get_catalog(username, type_name)
			try:
				docid = ds_intid.getId(obj)
				catalog.index_doc(docid, obj)
				counter = counter + 1
			except POSKeyError:
				# broken reference for object
				pass

	logger.debug('%s object(s) for user %s were reindexed' % (counter, username))
	
def evolve( context ):
	"""
	Evolve generation 9 to generation 10 by changing the root repoze catalog storage.
	"""
	conn = context.connection
	root = conn.root()

	search_conn = conn.get_connection( 'Search' )
	old_rds = search_conn.root()['repoze_datastore']
	
	container = root['nti.dataserver']
	lsm = container.getSiteManager()
	connection = getattr( lsm, '_p_jar', None )
	
	# create a new store
	repoze_datastore = create_repoze_datastore()
	lsm.registerUtility(repoze_datastore, provided=IRepozeDataStore)
	rsv = lsm.getUtility( nti_interfaces.IOIDResolver )
	if rsv._p_jar is None:
		rsv._p_jar = conn
	
	ds_intid = lsm.getUtility( provided=zope.intid.IIntIds )
		
	rds_users = set(old_rds.users.keys())
	for user in context.connection.root()['nti.dataserver']['users'].values():
		if user.username in rds_users:
			_reindex(connection, repoze_datastore, user, ds_intid)


