#!/usr/bin/env python
"""
zope.generations generation 27 evolver for nti.dataserver

$Id$
"""
from __future__ import print_function, unicode_literals

__docformat__ = 'restructuredtext'

generation = 27

from zope import component
from zope.component.hooks import site, setHooks

from nti.dataserver import interfaces as nti_interfaces

def _fake_missing_weak_ref():
	return None

def evolve( context ):
	"""
	Evolve generation 26 to generation 27 by making creators of changes be weakly refd.
	Also empties changes whose creator is no longer around.
	"""

	setHooks()
	ds_folder = context.connection.root()['nti.dataserver']
	with site( ds_folder ):
		assert component.getSiteManager() is ds_folder.getSiteManager(), "Hooks not installed?"

		users = ds_folder['users']
		for user in users.values():
			user._p_activate()
			stream_cache = user.__dict__.get( 'streamCache' )
			if stream_cache is None:
				continue

			for container in stream_cache.values():
				if container is None:
					continue
				for change in container:
					change._p_activate()
					change_creator = change.__dict__.get( 'creator' )
					if nti_interfaces.IUser.providedBy( change_creator ):
						if change_creator.username not in users:
							# OK, the user would be gone, except for these dangling refs
							change.__dict__['creator'] = _fake_missing_weak_ref
							change.__dict__['objectReference'] = _fake_missing_weak_ref
							change._p_changed = True
						else:
							change.creator = change_creator # let it set the weak ref
