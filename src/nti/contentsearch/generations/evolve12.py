from __future__ import print_function, unicode_literals

generation = 12

import zope.intid
from zope import component
from ZODB.POSException import POSKeyError
from zope.generations.utility import findObjectsProviding

from nti.dataserver import interfaces as nti_interfaces

from nti.contentsearch import interfaces as search_interfaces 

import logging
logger = logging.getLogger( __name__ )

def get_sharedWith(obj):
	# from IPython.core.debugger import Tracer;  Tracer()() ## DEBUG ##
	adapted = component.getAdapter(obj, search_interfaces.IContentResolver)
	if adapted and hasattr(adapted, "get_sharedWith"):
		result = adapted.get_sharedWith()
	else:
		result = ()
	return result

def _index(rim, obj, ds_intid):
	catalog = rim.get_create_catalog(obj)
	if catalog:
		docid = ds_intid.getId(obj)
		catalog.index_doc(docid, obj)
		return True
	return False

def _reindex(user, users, ds_intid, ignore_errors=False):
	username = user.username
	logger.debug('Reindexing object(s) for user %s' % username)
	
	counter = 0
	rim = search_interfaces.IRepozeEntityIndexManager(user, None)
	for obj in findObjectsProviding( user, nti_interfaces.IModeledContent):
		
		# ignore friends lists
		if nti_interfaces.IFriendsList.providedBy(obj):
			continue
		
		# index object
		try:
			if _index(rim, obj, ds_intid):
				counter = counter + 1
				for uname in get_sharedWith(obj):
					sharing_user = users.get(uname, None)
					if sharing_user and uname != username: 
						srim = search_interfaces.IRepozeEntityIndexManager(sharing_user, None)
						if srim is not None:
							_index(srim, obj, ds_intid)
		except POSKeyError:
			pass # broken reference for object
		except Exception:
			if not ignore_errors:
				raise
			pass

	logger.debug('%s object(s) for user %s were reindexed' % (counter, username))
	
def do_evolve(context):
	conn = context.connection
	root = conn.root()
	container = root['nti.dataserver']
	lsm = container.getSiteManager()
	users = context.connection.root()['nti.dataserver']['users']
	
	ds_intid = lsm.getUtility( provided=zope.intid.IIntIds )
	
	# make sure we register/provide the intid so it can be found
	component.provideUtility(ds_intid, zope.intid.IIntIds )
	for user in users.values():
		_reindex(user, users, ds_intid)
		
def evolve(context):
	"""
	Evolve generation 11 to generation 12 by reindexing in the user space
	"""
	conn = context.connection
	search_conn = conn.get_connection( 'Search' )
	search_conn.root().pop('repoze_datastore', None)
	do_evolve(context)
		
