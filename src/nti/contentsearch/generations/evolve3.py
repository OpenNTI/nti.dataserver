from __future__ import print_function, unicode_literals

__docformat__ = 'restructuredtext'

generation = 3

from nti.dataserver.ntiids import get_parts
from nti.dataserver.datastructures import fromExternalOID

from nti.contentsearch.common import get_type_name

import logging
logger = logging.getLogger( __name__ )

def evolve( context ):
	"""
	Evolve generation 2 to generation 3 by reindexing objects by object id
	"""
	conn = context.connection
	root = conn.root()
	
	container = root['nti.dataserver']
	lsm = container.getSiteManager()
	connection = getattr( lsm, '_p_jar', None )
	
	search_conn = conn.get_connection( 'Search' )
	rds = search_conn.root()['repoze_datastore']
	
	for username in list(rds.users.keys()):
		
		logger.debug('Reindexing search documents for user %s' % username)
		
		docids = list(rds.get_docids(username))
		for docid in docids:
			ntiid = rds.address_for_docid(username, docid)
			if ntiid:
				try:
					# from an ntiid get the external oid
					parts = get_parts( ntiid )
					oid_string = parts.specific
					
					# get internal oid and db name
					db_oid, database_name = fromExternalOID( oid_string )
					if database_name: 
						connection = connection.get_connection( database_name )
						
					obj = connection[db_oid] if db_oid and connection else None				
					if obj and oid_string:
			
						type_name = get_type_name(obj)
						catalog = rds.get_catalog(username, type_name)
						
						# unindex old doc
						logger.debug("unindexing '%s' for NTIID (%s,%s)" % (docid, type_name, ntiid))
						rds.remove_docid(username, docid)
						catalog.unindex_doc(docid)
						
						# reindex with object id
						docid = rds.add_address(username, oid_string)
						catalog.index_doc(docid, obj)
				
						logger.debug("new docid '%s' for oid '%s'" % (docid, oid_string))
					else:
						logger.warn("Could not find object with NTIID '%s'" % ntiid)
				except:
					logger.exception("Could not migrate object with NTIID '%s'" % ntiid)

	