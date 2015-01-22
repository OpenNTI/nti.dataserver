#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Generation 53 evolver

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 53

from zope import component
from zope.component.hooks import site
from zope.component.hooks import setHooks

from ZODB.POSException import POSError

BROKEN = ('nti.salesforce.users.SalesforceTokenInfo',
		  'nti.contentsearch._repoze_adpater._RepozeEntityIndexManager')

def do_evolve(context):

	setHooks()
	conn = context.connection
	root = conn.root()
	ds_folder = root['nti.dataserver']

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
			try:
				annotations = user.__annotations__
				for name in BROKEN:
					annotations.pop(name, None)
			except AttributeError:
				pass
		if bad_usernames:
			logger.warn( "Found %s bad users", bad_usernames )
		logger.info('Dataserver evolution %s done', generation)

def evolve(context):
	"""
	Evolve to generation 53 by removing knwon broken objects
	"""
	do_evolve(context)
