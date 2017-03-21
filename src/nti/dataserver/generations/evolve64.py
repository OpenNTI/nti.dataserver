#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 64

from zope import component

from zope.annotation.interfaces import IAnnotations

from zope.component.hooks import site, setHooks

from nti.base._compat import unicode_

from nti.dataserver.interfaces import ICommunity
from nti.dataserver.users.interfaces import ICommunityProfile
from nti.dataserver.users.user_profile import FRIENDLY_NAME_KEY

def do_evolve(context):
	setHooks()
	conn = context.connection
	root = conn.root()
	dataserver_folder = root['nti.dataserver']

	with site(dataserver_folder):
		assert	component.getSiteManager() == dataserver_folder.getSiteManager(), \
				"Hooks not installed?"

		users = dataserver_folder['users']
		for entity in users.values():
			if not ICommunity.providedBy(entity):
				continue
			profile = ICommunityProfile(entity)
			annotations = IAnnotations(entity)
			friendly = annotations.pop(FRIENDLY_NAME_KEY, None)
			if friendly is not None:
				profile.alias = unicode_(getattr(friendly, 'alias', None))
				profile.realname = unicode_(getattr(friendly, 'realname', None))

	logger.info('Dataserver evolution %s done.', generation)

def evolve(context):
	"""
	Evolve to 64 by migrating community profiles
	"""
	do_evolve(context)
