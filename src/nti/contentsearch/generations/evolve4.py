from __future__ import print_function, unicode_literals

__docformat__ = 'restructuredtext'

generation = 4

from ZODB.POSException import POSKeyError
from nti.dataserver.datastructures import fromExternalOID

from nti.contentsearch.common import get_type_name
from nti.contentsearch.common import indexable_type_names

import logging
logger = logging.getLogger( __name__ )

def _remove(rds, username, docid):
	rds.remove_docid(username, docid)
	for type_name in indexable_type_names:
		catalog = rds.get_catalog(username, type_name)
		try:
			catalog.unindex_doc(docid)
		except:
			pass
	
def evolve( context ):
	"""
	Evolve generation 3 to generation 4 by reindexing objects to change object id format
	"""
	conn = context.connection
	root = conn.root()
	
	container = root['nti.dataserver']
	lsm = container.getSiteManager()
	connection = getattr( lsm, '_p_jar', None )
	
	search_conn = conn.get_connection( 'Search' )
	rds = search_conn.root()['repoze_datastore']
	
	for username in list(rds.users.keys()):
		
		docids = list(rds.get_docids(username))
		logger.debug('Reindexing %s search documents for user %s' % (len(docids), username))
		
		for x, docid in enumerate(docids):
			oid_string = rds.address_for_docid(username, docid)
			if oid_string:
				try:
					# get internal oid and db name
					db_oid, database_name = fromExternalOID( oid_string )
					if database_name: 
						connection = connection.get_connection( database_name )
						
					obj = connection[db_oid] if db_oid and connection else None				
					if obj:
						type_name = get_type_name(obj)
						catalog = rds.get_catalog(username, type_name)
						
						# reindex
						logger.debug("reindexing (%s) '%s' (%s,%r)" % (x, docid, type_name, oid_string))
						catalog.reindex_doc(docid, obj)
					else:
						logger.warn("Could not find object with OID %r" % oid_string)
				except POSKeyError:
					logger.warn("Object with OID %r not in database" % oid_string)
					_remove(rds, username, docid)
				except:
					logger.exception("Could not migrate object with OID %r" % oid_string)
					
		logger.debug('Reindexing for user %s completed' % username)

	