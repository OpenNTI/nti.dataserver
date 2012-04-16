from __future__ import print_function, unicode_literals

__docformat__ = 'restructuredtext'

generation = 5

from zope.generations.utility import findObjectsMatching
from nti.dataserver.datastructures import fromExternalOID

from nti.dataserver.chat import MessageInfo
from nti.dataserver.contenttypes import Note
from nti.dataserver.contenttypes import Highlight
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
		
	# get chat messages b/c they will not be found easily in the 
	# user container objects
	messages = []
	docids = rds.get_docids(username)
	for docid in docids:
		connection = ds_conn
		oid_string = rds.address_for_docid(username, docid)
		db_oid, database_name = fromExternalOID( oid_string )
		if database_name: 
			connection = ds_conn.get_connection( database_name )
			
		try:
			obj = connection[db_oid] if db_oid and connection else None
			if isinstance(obj, MessageInfo):
				messages.append(obj)
		except:
			pass
		
	# remove user catalogs
	rds.remove_user(username)
	
	# recreate catalogs
	for type_name in indexable_type_names:
		catalog = create_catalog(type_name)
		rds.add_catalog(username, catalog, type_name)
		
	def _indexer(obj):
		type_name = get_type_name(obj)
		address = toExternalOID(obj)
		catalog = rds.get_catalog(username, type_name)
		docid = rds.get_or_create_docid_for_address(username, address)
		catalog.index_doc(docid, obj)

	counter = 0
	for obj in findObjectsMatching( user, lambda x: isinstance(x, (Note, Highlight))):
		_indexer(obj)
		counter = counter + 1
	
	logger.debug('%s note/hightlight object(s) for user %s were reindexed' % (counter, username))
	
	counter = 0
	for obj in messages:
		_indexer(obj)
		counter = counter + 1
		
	logger.debug('%s chat messages object(s) for user %s were reindexed' % (counter, username))

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

