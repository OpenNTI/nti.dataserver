from __future__ import print_function, unicode_literals

__docformat__ = 'restructuredtext'

generation = 3

from nti.dataserver.ntiids import get_parts
from nti.dataserver.datastructures import toExternalOID
from nti.dataserver.datastructures import fromExternalOID

from nti.contentsearch.common import get_type_name

import logging
logger = logging.getLogger( __name__ )

def evolve( context ):
	"""
	Evolve generation 2 to generation 3 by reindexing objects by object id
	"""
	conn = context.connection
	search_conn = conn.get_connection( 'Search' )
	
	root = conn.root()
	container = root['nti.dataserver']
	lsm = container.getSiteManager()
	connection = getattr( lsm, '_p_jar', None )
	rds = search_conn.root()['repoze_datastore']
	
	for username in list(rds.users.keys()):
		
		logger.debug('Reindexing search documents for user %s' % username)
		
		docids = list(rds.get_docids(username))
		for docid in docids:
			address = rds.address_for_docid(username, docid)
			if address:
				try:
					parts = get_parts( address )
					oid_string = parts.specific
					oid_string, _ = fromExternalOID( oid_string )

					obj = connection[oid_string]					
					if obj and oid_string:
			
						type_name = get_type_name(obj)
						catalog = rds.get_catalog(username, type_name)
						
						# unindex old doc
						logger.debug("unindexing '%s' for address (%s,%s)" % (docid, type_name, address))
						rds.remove_docid(username, docid)
						catalog.unindex_doc(docid)
						
						# reindex with object id
						docid = rds.add_address(username, oid_string)
						catalog.index_doc(docid, obj)
				
						logger.debug("new docid '%s' for oid '%s'" % (docid, toExternalOID(obj)))
					else:
						logger.warn("Could not find object with NTIID '%s'" % address)
				except:
					logger.exception("Could not migrate object with NTIID '%s'" % address)

	