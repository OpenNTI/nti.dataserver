from __future__ import print_function, unicode_literals

__docformat__ = 'restructuredtext'

generation = 6

from nti.contentsearch._document import DocumentMap

import logging
logger = logging.getLogger( __name__ )


def evolve( context ):
	"""
	Evolve generation 5 to generation 6 by using a new document map for each user
	"""
	conn = context.connection
	search_conn = conn.get_connection( 'Search' )
	rds = search_conn.root()['repoze_datastore']
	
	users = rds.get('users', {})
	for username in list(users.keys()):
		logger.debug('migrating document map for user %s' % username)
		old_dm = rds.docmaps.pop(username, None)
		if old_dm:
			docMap = DocumentMap()
			docMap.docid_to_address.update(old_dm.docid_to_address)
			docMap.address_to_docid.update(old_dm.address_to_docid)
			rds.docmaps[username] = docMap
			logger.debug("migration completed (%s,%s)" % 
						 (len(docMap.docid_to_address), len(docMap.address_to_docid)) )
			

