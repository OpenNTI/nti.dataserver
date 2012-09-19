#!/usr/bin/env python
"""
zope.generations generation 26 evolver for nti.dataserver

$Id$
"""
from __future__ import print_function, unicode_literals

__docformat__ = 'restructuredtext'

generation = 26

from zope import component
from zope.component.hooks import site, setHooks

def evolve( context ):
	"""
	Evolve generation 25 to generation 26 by giving parents and names to stream
	cache objects.
	"""

	setHooks()
	ds_folder = context.connection.root()['nti.dataserver']
	with site( ds_folder ):
		assert component.getSiteManager() == ds_folder.getSiteManager(), "Hooks not installed?"

		users = ds_folder['users']
		for user in users.values():
			# Note that this is missing DFLs which is the only non-user place these could be
			user._p_activate()
			for k in ('streamCache', 'containersOfShared', 'containers_of_muted' ):
				if k in user.__dict__:
					v = user.__dict__[k]
					v.__parent__ = user
					v.__name__ = k
