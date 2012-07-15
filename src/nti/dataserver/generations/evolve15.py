#!/usr/bin/env python
"""
zope.generations generation 15 evolver for nti.dataserver

$Id$
"""
from __future__ import print_function, unicode_literals

__docformat__ = 'restructuredtext'

generation = 15

import BTrees
from zope.generations.utility import findObjectsMatching

from nti.dataserver import sharing



def evolve( context ):
	"""
	Evolve generation 14 to generation 15 by finding objects that are ShareableMixins
	and making their data be sets of usernames.
	"""
	for mixin in findObjectsMatching( context.connection.root()['nti.dataserver'],
									  lambda x: isinstance(x, sharing.ShareableMixin) and x.__dict__.get( '_sharingTargets' ) ):

		treeset = BTrees.family64.OO.TreeSet( )
		for target in mixin.__dict__['_sharingTargets']:
			treeset.add( getattr( target, 'username', target ) )
		mixin._sharingTargets = treeset
