from __future__ import print_function, unicode_literals

import zope.intid
from zope import component
from zc import intid as zc_intid
from ZODB.POSException import POSKeyError

from nti.dataserver.users import friends_lists

from nti.contentsearch.utils import get_uid
from nti.contentsearch.utils import find_all_indexable_pairs
from nti.contentsearch import interfaces as search_interfaces 
from nti.contentsearch.utils._repoze_utils import remove_entity_catalogs
						
import logging
logger = logging.getLogger( __name__ )

def reindex_ugd(user, users_get, ds_intid):
	username = user.username
	logger.debug('Reindexing object(s) for %s' % username)
	
	counter = 0
	dfl_names = set()
	
	for e, obj in find_all_indexable_pairs(user, user_get=users_get, include_dfls=True):
		
		# if we find a DFL clear its catalogs
		if isinstance(e, friends_lists.DynamicFriendsList) and e.username not in dfl_names:
			remove_entity_catalogs(e)
			dfl_names.add(e.username)
		
		rim = search_interfaces.IRepozeEntityIndexManager(e, None)
		try:
			catalog = rim.get_create_catalog(obj) if rim is not None else None
			if catalog is not None:
				docid = get_uid(obj, ds_intid)
				if docid is not None:
					catalog.index_doc(docid, obj)
					counter = counter + 1
				else:
					logger.warn("Cannot find int64 id for %r. Object will not be indexed" % obj)
		except POSKeyError:
			# broken reference for object
			pass
	
	logger.debug('%s object(s) for user %s were reindexed' % (counter, username))
	
	return counter
	
def reindex_all(context):
	conn = context.connection
	root = conn.root()
	container = root['nti.dataserver']
	lsm = container.getSiteManager()
	users = context.connection.root()['nti.dataserver']['users']
	
	ds_intid = lsm.getUtility( provided=zope.intid.IIntIds )
	component.provideUtility(ds_intid, zope.intid.IIntIds )
	component.provideUtility(ds_intid, zc_intid.IIntIds )
	
	# remove all catalogs first
	for user in users.values():
		remove_entity_catalogs(user)
		
	# reindex all users ugd
	for user in users.values():
		reindex_ugd(user, users.get, ds_intid)
		
	logger.debug('Evolution done!!!')

		
