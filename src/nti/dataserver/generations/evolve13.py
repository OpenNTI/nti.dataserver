#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
zope.generations generation 13 evolver for nti.dataserver

$Id$
"""
from __future__ import print_function, unicode_literals

__docformat__ = 'restructuredtext'

generation = 13



from zope.location.location import locate
from zope.generations.utility import findObjectsMatching


from nti.dataserver import users
from nti.dataserver import interfaces as nti_interfaces

def evolve( context ):
	"""
	Evolve generation 12 to generation 13 by setting the parents and names
	of containers in users.

	"""
	root = context.connection.root()
	dataserver_folder = root['nti.dataserver']


	# Finally fix up the container names.
	# Note that we're looking for User objects, which also catches Provider objects
	for user in findObjectsMatching( dataserver_folder, lambda x: isinstance(x,users.User) ):
		if user.containers.__parent__ is None:
			user.containers.__parent__ = user
			user.containers.__name__ = ''

			for name, container in user.containers.iteritems():
				if nti_interfaces.ILocation.providedBy( container ) and container.__parent__ is None:
					locate( container, user.containers, name )
