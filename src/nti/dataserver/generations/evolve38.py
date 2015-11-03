#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 38

from zope import component
from zope.component.hooks import site, setHooks

def evolve( context ):
	"""
	Evolve generation 37 to generation 38 by correcting a few small mistakes.
	"""
	setHooks()
	ds_folder = context.connection.root()['nti.dataserver']
	with site( ds_folder ):
		assert component.getSiteManager() == ds_folder.getSiteManager(), "Hooks not installed?"

		# First, prior to r8718, we used a simple call to locate() to
		# establish this parent child relationship, so databases
		# older than that will not have the right containment
		root = ds_folder.__parent__
		if ds_folder.__name__ not in root:
			root[ds_folder.__name__] = ds_folder

		# Next, some very ancient user-like things may have non-unicode name values
		users = ds_folder['users']
		for user in users.values():
			try:
				if isinstance( user.username, bytes ):
					# go through the dict to be sure we don't hit
					# any new validation or fire any events
					user.__dict__['username'] = unicode( user.username, 'utf-8' )
					user._p_changed = True
					logger.debug( "Updated user name %s", user.username )
			except (KeyError, AttributeError):
				pass
