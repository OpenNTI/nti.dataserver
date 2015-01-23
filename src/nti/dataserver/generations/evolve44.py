#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 44

from zope import component
from zope.event import notify
from zope.component.hooks import site, setHooks

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import ICommunity
from nti.dataserver.interfaces import StartDynamicMembershipEvent

def evolve( context ):
	"""
	Evolve generation 43 to 44 by indexing community memberships.
	"""
	setHooks()
	ds_folder = context.connection.root()['nti.dataserver']
	users_folder = ds_folder['users']
	with site( ds_folder ):
		assert component.getSiteManager() == ds_folder.getSiteManager(), "Hooks not installed?"

		for username, user in users_folder.items():
			try:
				if not IUser.providedBy(user):
					continue

				for com in user.dynamic_memberships:
					if ICommunity.providedBy(com):
						notify(StartDynamicMembershipEvent(user, com))
			except KeyError:
				logger.warn("Invalid user %s", username)
