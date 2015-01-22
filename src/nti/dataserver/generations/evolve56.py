#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 6

from zope import component
from zope.catalog.interfaces import ICatalog
from zope.component.hooks import site, setHooks

from ZODB.POSException import POSError

from nti.app.products.ou.interfaces import IOUUser
from nti.app.products.ou.interfaces import IOUUserProfile

from nti.dataserver.users.index import CATALOG_NAME

def do_evolve(context):
	setHooks()
	conn = context.connection
	root = conn.root()
	ds_folder = root['nti.dataserver']
	lsm = ds_folder.getSiteManager()
	
	count = 0
	with site(ds_folder):
		assert	component.getSiteManager() == ds_folder.getSiteManager(), \
				"Hooks not installed?"

		ent_catalog = lsm.getUtility(provided=ICatalog, name=CATALOG_NAME)

		users = ds_folder['users']
		for username, user in users.items():
			try:
				user._p_activate()
			except (POSError, KeyError): # pragma: no cover
				logger.warn( "Invalid user %s. Shard not mounted?", username )
				continue
			
			if IOUUser.providedBy(user) or ILinkedInUser.providedBy(user):
				interface.noLongerProvides(user, ISymmysUser)
				interface.noLongerProvides(user, ILinkedInUser)
				interface.alsoProvides(user, ISymmysPerson)
				count += 1
			
		if bad_usernames:
			logger.warn( "Found %s bad users", bad_usernames )
		
		logger.info('Dataserver evolution %s done. %s user(s) migrated', 
					generation, count)
		return count
		
def evolve( context ):
	"""
	Evolve to generation 55 verifying emails for known sites
	"""
	do_evolve(context)
