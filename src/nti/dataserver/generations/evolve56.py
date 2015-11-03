#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 56

import zope.intid

from zope import component
from zope.catalog.interfaces import ICatalog
from zope.component.hooks import site, setHooks

from ZODB.POSException import POSError

from ..users.index import IX_TOPICS
from ..users.index import CATALOG_NAME
from ..users.index import IX_EMAIL_VERIFIED
from ..users.interfaces import IUserProfile

def do_evolve(context):
	setHooks()
	conn = context.connection
	root = conn.root()
	ds_folder = root['nti.dataserver']
	lsm = ds_folder.getSiteManager()
	
	interfaces  = []
	try:
		from nti.app.sites.symmys.interfaces import ISymmysPerson
		interfaces.append((ISymmysPerson, IUserProfile))
	except ImportError:
		pass
	
	try:
		from nti.app.sites.okstate.interfaces import IOKStateUser
		interfaces.append((IOKStateUser, IUserProfile))
	except ImportError:
		pass
	
	count = 0
	with site(ds_folder):
		assert	component.getSiteManager() == ds_folder.getSiteManager(), \
				"Hooks not installed?"

		intids = lsm.getUtility(zope.intid.IIntIds)
		ent_catalog = lsm.getUtility(provided=ICatalog, name=CATALOG_NAME)
		topics = ent_catalog[IX_TOPICS]
		email_verified = topics[IX_EMAIL_VERIFIED]
		
		users = ds_folder['users']
		for username, user in users.items():
			try:
				user._p_activate()
			except (POSError, KeyError): # pragma: no cover
				logger.warn( "Invalid user %s. Shard not mounted?", username )
				continue
			
			uid = intids.queryId(user)
			if uid is None:
				logger.warn( "Invalid user %s. User with no intid", username )
				continue
			
			for i_user, i_profile in interfaces:
				if not i_user.providedBy(user):
					continue
				profile = i_profile(user, None)
				if profile is None:
					continue
				
				if not getattr(profile, 'email_verified', False):
					profile.email_verified = True
					email_verified.index_doc(uid, user)
					count += 1

		logger.info('Dataserver evolution %s done. %s user(s) updated', 
					generation, count)
		return count
		
def evolve( context ):
	"""
	Evolve to generation 56 by verifying emails for users in trusted sites 
	"""
	do_evolve(context)
