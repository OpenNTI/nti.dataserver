from __future__ import print_function, unicode_literals

__docformat__ = 'restructuredtext'

generation = 9

from ZODB.POSException import POSKeyError
from zope.generations.utility import findObjectsMatching
from zope.generations.utility import findObjectsProviding

from nti.externalization.oids import toExternalOID
from nti.dataserver import interfaces as nti_interfaces

from nti.contentsearch.common import redaction_

import logging
logger = logging.getLogger( __name__ )

def _reindex(ds_conn, rds, user):
	username = user.username
	logger.debug('Reindexing redactions(s) for user %s' % username)

	# remove and create catalog 
	rds.remove_catalog(username, redaction_)
	catalog = rds.get_catalog(username, redaction_)
	
	counter = 0
	for obj in findObjectsProviding(user, nti_interfaces.IRedaction):
		try:
			address = toExternalOID(obj)
			docid = rds.get_or_create_docid_for_address(username, address)
			catalog.index_doc(docid, obj)
			counter = counter + 1
		except POSKeyError:
			# broken reference for object
			pass

	logger.debug('%s redaction(s) for user %s were reindexed' % (counter, username))

def evolve( context ):
	"""
	Evolve generation 8 to generation 9 by reindexing all redactions for all users if required
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
