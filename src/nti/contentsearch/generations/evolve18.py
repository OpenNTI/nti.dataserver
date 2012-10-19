from __future__ import print_function, unicode_literals

generation = 18

import zope.intid
from zope import component
from zope.generations.utility import findObjectsProviding

from nti.dataserver.users import friends_lists
from nti.dataserver import interfaces as nti_interfaces
from nti.contentsearch.common import (ngrams_, content_)
from nti.contentsearch import interfaces as search_interfaces 
from nti.contentsearch._repoze_index import _zopytext_field_creator

import logging
logger = logging.getLogger( __name__ )

def evolve(context):
	"""
	Evolve generation 17 to 18 by checking if DFLs have been migrated successfully
	"""
	
	conn = context.connection
	root = conn.root()
	container = root['nti.dataserver']
	lsm = container.getSiteManager()
	users = context.connection.root()['nti.dataserver']['users']
	
	ds_intid = lsm.getUtility( provided=zope.intid.IIntIds )
	component.provideUtility(ds_intid, zope.intid.IIntIds )	

	for user in users.values():		
		for obj in findObjectsProviding( user, nti_interfaces.IFriendsList):
			
			if not isinstance(obj, friends_lists.DynamicFriendsList):
				continue
			
			rim = search_interfaces.IRepozeEntityIndexManager(obj)
			for name, catalog in rim.items():
				if ngrams_ not in catalog:
					
					logger.debug("migrating %s for user %s, catalog %s" % (obj, user, name))
					
					# add field
					_zopytext_field_creator(catalog, ngrams_, None)
				
					# reindex existing
					counter = 0
					field = catalog.get(content_)
					docids = field.get_docids()
					for docid in docids:
						data = ds_intid.queryObject(docid, None)
						if data is not None:
							counter += 1
							catalog.reindex_doc(docid, data)
							
					logger.debug("%s object(s) migrated for %s, catalog %s" % (counter, obj, name))
		
			

