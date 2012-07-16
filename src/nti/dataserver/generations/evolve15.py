#!/usr/bin/env python
"""
zope.generations generation 15 evolver for nti.dataserver

$Id$
"""
from __future__ import print_function, unicode_literals

__docformat__ = 'restructuredtext'

generation = 15

import collections
import BTrees
import persistent.wref
from zope.generations.utility import findObjectsMatching

from nti.dataserver import sharing

def migrate( user, mixin ):
	assert isinstance( mixin, sharing.ShareableMixin )
	treeset = BTrees.family64.OO.TreeSet( )
	targets = mixin.__dict__.get('_sharingTargets', ())
	targets = targets or ()

	def addToSet(target):
		if isinstance( target, basestring ):
			treeset.add( target )
		elif isinstance( target, collections.Iterable ):
			# Walk into friends lists
			for x in target: addToSet( x )
		else:
			treeset.add( target.username )

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
	Evolve generation 14 to generation 15 by finding objects that are ShareableMixins
	and making their data be sets of usernames.
	"""

	# Walk into weak refs too...
	def wref_values(self):
		yield self()
	persistent.wref.WeakRef.values = wref_values

	for user in context.connection.root()['nti.dataserver']['users'].values():
		for mixin in findObjectsMatching( user,
										  needs_migrate):
			migrate( user, mixin )
