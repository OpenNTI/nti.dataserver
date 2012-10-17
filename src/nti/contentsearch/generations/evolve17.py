from __future__ import print_function, unicode_literals

generation = 17

import zope.intid
from zope import component

from evolve12 import reindex_ugd
from evolve14 import do_remove_user_catalogs

from nti.contentsearch.common import ngrams_ 
from nti.contentsearch import interfaces as search_interfaces 

def evolve(context):
	"""
	Evolve generation 16 to 17 by checking if catalogs have been migrated successfully when adding the ngrams field
	"""
	
	conn = context.connection
	root = conn.root()
	container = root['nti.dataserver']
	lsm = container.getSiteManager()
	users = context.connection.root()['nti.dataserver']['users']
	
	ds_intid = lsm.getUtility( provided=zope.intid.IIntIds )
	component.provideUtility(ds_intid, zope.intid.IIntIds )

	for user in users.values():
		rim = search_interfaces.IRepozeEntityIndexManager(user)
		migrate = False
		for catalog in rim.values():
			if ngrams_ not in catalog:
				migrate = True
				break
		
		if migrate:
			do_remove_user_catalogs(user)
			reindex_ugd(user, users, ds_intid)
			

