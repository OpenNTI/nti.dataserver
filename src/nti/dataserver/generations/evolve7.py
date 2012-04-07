#!/usr/bin/env python
"""zope.generations generation 7 evolver for nti.dataserver
$Id$
"""
from __future__ import print_function, unicode_literals

__docformat__ = 'restructuredtext'

generation = 7

from zope.generations.utility import findObjectsMatching

from nti.dataserver import users, datastructures, interfaces as nti_interfaces
from BTrees.OOBTree import OOTreeSet

def evolve( context ):
	"""
	Evolve generation 6 to generation 7 by changing all users' passwords to bcrypt.
	"""
	for user in findObjectsMatching( context.connection.root()['nti.dataserver'].getSiteManager(), lambda x: nti_interfaces.IUser.providedBy( x ) ):
		password = user.password # Read the string
		user.password = password # reset and hash
