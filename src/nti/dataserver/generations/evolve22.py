#!/usr/bin/env python
"""
zope.generations generation 22 evolver for nti.dataserver

$Id$
"""
from __future__ import print_function, unicode_literals

__docformat__ = 'restructuredtext'

generation = 22

import BTrees
from zope.generations.utility import findObjectsMatching

from zope import component
from zope.component.hooks import site, setHooks
import zope.intid
from nti.dataserver import sharing

def migrate( user, mixin, intids, users ):
	assert isinstance( mixin, sharing.ShareableMixin )
	treeset = BTrees.family64.II.TreeSet( )
	targets = mixin.__dict__.get('_sharingTargets', ())
	if isinstance( targets, BTrees.family64.II.TreeSet ):
		mixin._v_migrated = True
		return

	targets = targets or ()

	def addToSet(target):
		target = users.get( target )
		if target:
			treeset.add( intids.register( target ) )

	for target in targets:
		addToSet( target )

	if not treeset:
		if '_sharingTargets' in mixin.__dict__:
			del mixin._sharingTargets
	else:
		mixin._sharingTargets = treeset

	mixin._v_migrated = True

def needs_migrate(x):
	return isinstance( x, sharing.ShareableMixin) and not getattr( x, '_v_migrated', False )

def evolve( context ):
	"""
	Evolve generation 21 to generation 22 by finding objects that are ShareableMixins
	and making their data be sets of intids of usernames.
	"""

	setHooks()
	ds_folder = context.connection.root()['nti.dataserver']
	with site( ds_folder ):
		assert component.getSiteManager() == ds_folder.getSiteManager(), "Hooks not installed?"

		intids = component.getUtility( zope.intid.IIntIds )
		users = ds_folder['users']
		for user in users.values():
			for mixin in findObjectsMatching( user,
											  needs_migrate):
				__traceback_info__ = user, mixin
				migrate( user, mixin, intids, users )

		# Everyone may not have been registered with an intid, ensure it is
		intids.register( users['Everyone'] )
