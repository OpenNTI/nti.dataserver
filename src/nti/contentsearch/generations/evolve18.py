from __future__ import print_function, unicode_literals

generation = 18

import zope.intid
from zope import component

from nti.contentsearch.common import (ngrams_, content_)
from nti.contentsearch import interfaces as search_interfaces 
from nti.contentsearch._repoze_index import _zopytext_field_creator

import logging
logger = logging.getLogger( __name__ )

def evolve(context):
	"""
	Evolve generation 17 to 18 by checking if DFLs and communities have been migrated successfully
	"""
	
	conn = context.connection
	root = conn.root()
	container = root['nti.dataserver']
	lsm = container.getSiteManager()
	users = context.connection.root()['nti.dataserver']['users']
	
	ds_intid = lsm.getUtility( provided=zope.intid.IIntIds )
	component.provideUtility(ds_intid, zope.intid.IIntIds )
	
	for user in users.values():
		communities = user.communities if user and hasattr(user, 'communities') else ()
		for c in communities:
			rim = search_interfaces.IRepozeEntityIndexManager(c, None)
			if rim is None:
				continue
			
			for name, catalog in rim.items():
				if ngrams_ not in catalog:
					
					logger.debug("migrating %s for user %s, catalog %s" % (c, user, name))
					
					_zopytext_field_creator(catalog, ngrams_)
					
					# get object ids
					field = catalog.get(content_)
					docids = field.get_docids()
					for docid in docids:
						obj = ds_intid.queryObject(docid, None)
						if obj is not None:
							catalog.reindex_doc(docid, obj)
		
			

