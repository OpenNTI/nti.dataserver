from __future__ import print_function, unicode_literals

__docformat__ = 'restructuredtext'

generation = 5

from ZODB.POSException import POSKeyError
from zope.generations.utility import findObjectsMatching
from zope.generations.utility import findObjectsProviding

from nti.dataserver.datastructures import toExternalOID
from nti.dataserver import interfaces as nti_interfaces

from nti.contentsearch.common import get_type_name
from nti.contentsearch.common import indexable_type_names
from nti.contentsearch._repoze_index import create_catalog

import logging
logger = logging.getLogger( __name__ )

def _reindex(ds_conn, rds, user):
	username = user.username
	logger.debug('Reindexing object(s) for user %s' % username)
		
	# remove user catalogs
	rds.remove_user(username)
	
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
				address = toExternalOID(obj)
				docid = rds.get_or_create_docid_for_address(username, address)
				catalog.index_doc(docid, obj)
				counter = counter + 1
			except POSKeyError:
				logger.warn('Broken reference for object %s. It will not be indexed' % obj)
	
	logger.debug('%s object(s) for user %s were reindexed' % (counter, username))

def evolve( context ):
	"""
	Evolve generation 4 to generation 5 by reindexing all objects for all users if required
	"""
	conn = context.connection
	root = conn.root()
	
	container = root['nti.dataserver']
	lsm = container.getSiteManager()
	connection = getattr( lsm, '_p_jar', None )
	
	search_conn = conn.get_connection( 'Search' )
	rds = search_conn.root()['repoze_datastore']
	
	rds_users = set(rds.users.keys())
	for user in findObjectsMatching(lsm, lambda x: nti_interfaces.IUser.providedBy( x )):
		if user.username in rds_users:
			_reindex(connection, rds, user)

