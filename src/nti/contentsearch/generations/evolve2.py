from __future__ import print_function, unicode_literals

__docformat__ = 'restructuredtext'

generation = 2

from BTrees.OOBTree import OOBTree
from repoze.catalog.document import DocumentMap

from nti.contentsearch.textindexng3 import CatalogTextIndexNG3
from nti.contentsearch.common import content_

import logging
logger = logging.getLogger( __name__ )

def evolve( context ):
	"""
	Evolve generation 1 to generation 2 by creating a docmap for every user in the repoze datastore
	"""
	conn = context.connection
	search_conn = conn.get_connection( 'Search' )
	rds = search_conn.root()['repoze_datastore']
	
	# remove the old doc map
	oldDocMap = rds.pop('docMap', {})
	docmaps = OOBTree()
	
	users = rds.get('users', {})
	for username in list(users.keys()):
		
		logger.debug('Migrating search documents for user %s' % username)
		
		# get/remove all catalogs
		pm = users.pop(username, {})
		
		docMap = DocumentMap()
		docmaps[username] = docMap
		
		for type_name, catalog in pm.items():
			
			logger.debug('Checking %s catalog' % type_name)
			
			textfield = catalog.get(content_, None)
			if isinstance(textfield, CatalogTextIndexNG3):
				docids = textfield.get_docids()
			else:
				docids = []
				
			logger.debug('%s docid(s) found in catalog %s' % (len(docids), type_name))
			
			for docid in docids:
				address = oldDocMap.address_for_docid(docid)
				if address:
					docMap.add(address, docid)
				else:
					logger.debug("Could not find address for docid %s" % docid)
		
		# catalogs now are in a new data structure
		ootree = OOBTree()
		ootree.update(pm)
		users[username] = ootree
		
	# restore new docmaps
	rds['docMap'] = docmaps
