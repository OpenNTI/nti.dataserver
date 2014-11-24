#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
schema generation installation.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 53

from zope import component
from zope.component.hooks import site
from zope.component.hooks import setHooks

from nti.dataserver.interfaces import IUser

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
		users = ds_folder['users']
		for user in users.values():
			if not IUser.providedBy(user):
				continue
			
			try:
				annotations = user.__annotations__
				for name in BROKEN:
					annotations.pop(name, None)
			except (AttributeError):
				pass
		logger.info('Dataserver evolution %s done', generation)

def evolve(context):
	do_evolve(context)

