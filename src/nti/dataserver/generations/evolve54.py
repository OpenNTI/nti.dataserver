#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Generation 54 evolver

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 54

from zope import component
from zope import interface
from zope.component.hooks import site
from zope.component.hooks import setHooks

from ZODB.POSException import POSError

def do_evolve(context):

	setHooks()
	conn = context.connection
	root = conn.root()
	ds_folder = root['nti.dataserver']

	try:
		from nti.app.sites.symmys.interfaces import ISymmysUser
		from nti.app.sites.symmys.interfaces import ILinkedInUser
		from nti.app.sites.symmys.interfaces import ISymmysPerson
	except ImportError:
		return
	
	count = 0
	with site(ds_folder):
		assert	component.getSiteManager() == ds_folder.getSiteManager(), \
				"Hooks not installed?"

		bad_usernames = []
		users = ds_folder['users']
		for username, user in users.items():
			try:
				user._p_activate()
			except (POSError, KeyError): # pragma: no cover
				logger.warn( "Invalid user %s. Shard not mounted?", username )
				bad_usernames.append( username )
				continue
			
			if ISymmysUser.providedBy(user) or ILinkedInUser.providedBy(user):
				interface.noLongerProvides(user, ISymmysUser)
				interface.noLongerProvides(user, ILinkedInUser)
				interface.alsoProvides(user, ISymmysPerson)
				count += 1
			
		if bad_usernames:
			logger.warn( "Found %s bad users", bad_usernames )
		
		logger.info('Dataserver evolution %s done. %s user(s) migrated', 
					generation, count)
		return count

def evolve(context):
	"""
	Evolve to generation 54 by updating interface for symmys users
	"""
	do_evolve(context)
