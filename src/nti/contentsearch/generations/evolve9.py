from __future__ import print_function, unicode_literals

__docformat__ = 'restructuredtext'

generation = 9

from ZODB.POSException import POSKeyError
from zope.generations.utility import findObjectsProviding

from nti.externalization.oids import toExternalOID
from nti.dataserver import interfaces as nti_interfaces

from nti.contentsearch.common import redaction_
from nti.contentsearch._repoze_index import create_catalog

import logging
logger = logging.getLogger( __name__ )

def _reindex(ds_conn, rds, user):
	username = user.username
	logger.debug('Reindexing redactions(s) for user %s' % username)

	# remove and create catalog 
	rds.remove_catalog(username, redaction_)
	catalog = create_catalog(redaction_)
	rds.add_catalog(username, catalog, redaction_)
	
	counter = 0
	for obj in findObjectsProviding(user, nti_interfaces.IRedaction):
		try:
			#from IPython.core.debugger import Tracer;  Tracer()() ## DEBUG ##
			address = toExternalOID(obj)
			docid = rds.get_or_create_docid_for_address(username, address)
			catalog.index_doc(docid, obj)
			counter = counter + 1
		except POSKeyError:
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
	for user in context.connection.root()['nti.dataserver']['users'].values():
		if user.username in rds_users:
			_reindex(connection, rds, user)
