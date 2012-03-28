#!/usr/bin/env python
"""zope.generations generation 6 evolver for nti.dataserver
$Id$
"""
from __future__ import print_function, unicode_literals

__docformat__ = 'restructuredtext'

generation = 6

from zope.generations.utility import findObjectsMatching

from nti.dataserver import users, datastructures, interfaces as nti_interfaces
from BTrees.OOBTree import OOTreeSet

def evolve( context ):
	"""
	Evolve generation 5 to generation 6 by changing all users's FriendsLists
	to be case insensitive
	"""
	for user in findObjectsMatching( conn.root()['nti.dataserver'].getSiteManager(), lambda x: nti_interfaces.IUser.providedBy( x ) ):
		friends_lists = user.getContainer( 'FriendsLists' )
		if friends_lists is not None:
			friends_lists._SampleContainer__data = datastructures.KeyPreservingCaseInsensitiveModDateTrackingOOBTree( friends_lists._SampleContainer__data )
