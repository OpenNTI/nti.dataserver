from __future__ import print_function, unicode_literals

generation = 12

from ZODB.POSException import POSKeyError
from zope.generations.utility import findObjectsProviding

from nti.dataserver import interfaces as nti_interfaces

from nti.contentsearch.interfaces import IRepozeUserIndexManager

import logging
logger = logging.getLogger( __name__ )

def reindex(user, ignore_errors=True):
	username = user.username
	logger.debug('Reindexing object(s) for user %s' % username)

	rim = IRepozeUserIndexManager(user, None)
	
	counter = 0
	for obj in findObjectsProviding( user, nti_interfaces.IModeledContent):
		try:
			if rim.index_content(obj) is not None:
				counter = counter + 1
		except POSKeyError:
			# broken reference for object
			pass
		except Exception:
			if not ignore_errors:
				raise
			pass

	logger.debug('%s object(s) for user %s were reindexed' % (counter, username))
	
def evolve(context):
	"""
	Evolve generation 11 to generation 12 by reindexing in the user space
	"""
	conn = context.connection
	search_conn = conn.get_connection( 'Search' )
	search_conn.root().pop('repoze_datastore', None)
	for user in context.connection.root()['nti.dataserver']['users'].values():
		reindex(user)