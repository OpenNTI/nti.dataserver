#!/usr/bin/env python
"""
zope.generations generation 28 evolver for nti.dataserver

$Id$
"""
from __future__ import print_function, unicode_literals

__docformat__ = 'restructuredtext'

generation = 28

from zope import component
from zope.component.hooks import site, setHooks

from nti.dataserver.users import Entity
from nti.dataserver.users.wref import WeakRef
import persistent.wref

import six

from BTrees.OOBTree import OOTreeSet

def _fake_missing_weak_ref():
	return None

def evolve( context ):
	"""
	Evolve generation 27 to generation 28 by adapting all friends list storage to the new weak refs.
	"""

	setHooks()
	ds_folder = context.connection.root()['nti.dataserver']
	with site( ds_folder ):
		assert component.getSiteManager() == ds_folder.getSiteManager(), "Hooks not installed?"

		users = ds_folder['users']
		for user in users.values():
			if not hasattr( user, 'friendsLists' ):
				continue
			for fl in user.friendsLists.itervalues():
				old_friends = getattr( fl, '_friends', None )
				if old_friends is None:
					continue
				delattr( fl, '_friends' )

				new_friends = OOTreeSet()
				setattr( fl, '_friends_wref_set', new_friends )

				for thing in old_friends:
					if isinstance( thing, persistent.wref.WeakRef ):
						thing = thing()

					if isinstance( thing, Entity ):
						# Entities already went through the add-friend process
						try:
							new_friends.add( WeakRef( thing ) )
						except KeyError:
							# Already deleted. Still has a weak ref, doesn't have a ntiid
							pass
					elif isinstance( thing, six.string_types ):
						# strings didn't. If they can be resolved, they must be
						entity = fl.get_entity( thing )
						if entity:
							fl.addFriend( entity )
