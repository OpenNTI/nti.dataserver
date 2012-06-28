#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
zope.generations generation 14 evolver for nti.dataserver

$Id$
"""
from __future__ import print_function, unicode_literals

__docformat__ = 'restructuredtext'

generation = 13

logger = __import__('logging').getLogger( __name__ )

from zope.generations.utility import findObjectsMatching


from nti.dataserver import users
from nti.dataserver import dicts
from nti.dataserver import containers
from nti.dataserver import datastructures
from nti.dataserver import interfaces as nti_interfaces

from BTrees.OOBTree import OOBTree

from nti.deprecated import hides_warnings

@hides_warnings
def evolve( context ):
	"""
	Evolve generation 13 to generation 14 by regenerating many of the container datastructures
	to use the new classes that are faster, safer, and more correct.

	"""
	root = context.connection.root()
	dataserver_folder = root['nti.dataserver']

	# alright, first the root folders
	for k in  ('users', 'vendors', 'library', 'quizzes', 'providers'):
		old_container = dataserver_folder[k]
		del dataserver_folder[k]
		dataserver_folder[k] = containers.CaseInsensitiveLastModifiedBTreeContainer()
		for ck, cv in old_container.items():
			if ck == 'Last Modified': continue
			dataserver_folder[k][ck] = cv

	# NOTE: There exists [quizzes][quizzes] but that's going away, not bothering with it.

	# All of the rest of the changed data is within the user/provider objects
	for user in findObjectsMatching( dataserver_folder, lambda x: isinstance(x,users.User) ):
		# First an easy one: the stream cache
		user.streamCache = OOBTree( user.streamCache )
		user.streamCache.pop( 'Last Modified', None )

		ucontainers = user.containers
		# Switch the type for newly created containers
		ucontainers.containerType = containers.LastModifiedBTreeContainer
		# Copy the existing containers-of-containers to the new type
		ucontainers.containers = dicts.CaseInsensitiveLastModifiedDict( ucontainers.containers )
		# Move the last modified data (if present)
		lm = ucontainers.containers.pop( 'Last Modified', 0 )
		if lm:
			ucontainers.containers.lastModified = lm

		# Now the individual containers themselves. Either
		# it is a generic container of type datastructures.ModDateTrackingBTreeContainer, or it is a
		# custom subclass, which should implement INamedContainer.
		# The generic containers should be children of ucontainers. The others should
		# be children of the user. We assert all of this to make sure we don't miss something
		i = 0
		for k, container in list(ucontainers.containers.items()):
			__traceback_info__ = user, k, container, container.__parent__, ucontainers
			i += 1
			if nti_interfaces.INamedContainer.providedBy( container ):
				# In some cases, we missed setting parents on old objects, specifically devices.
				# If that's so, then reparent it
				if (container.__parent__ is ucontainers or container.__parent__ is None) and k in ( 'Devices', 'FriendsLists', 'Classes'):
					container.__parent__ = user
				assert container.__parent__ is user
				assert isinstance( container, datastructures.AbstractNamedLastModifiedBTreeContainer )
				# For these, we want to leave the wrapper alone, since it will now
				# take care of the case mangling (if necessary). We just want to change the BTree implementation
				# Unfortunately, we must manually copy it over to get the keys mangled correctly (since in some
				# cases we're going from case-sensitive to case-insensitive
				old_data = container._SampleContainer__data
				lm = old_data.pop( 'Last Modified', 0 )
				new_data = OOBTree()
				tx_key = containers._tx_key_insen if isinstance( container, datastructures.AbstractCaseInsensitiveNamedLastModifiedBTreeContainer ) else lambda x: x
				for k, v in old_data.items():
					__traceback_info__ = (k, v) + __traceback_info__
					new_data[tx_key(getattr(k, 'key', k))] = v
				container._SampleContainer__data = new_data
				# These will be missing a 'Last Modified' attribute, so make sure they get it
				container._lastModified = containers.NumericMaximum( lm )
			else:
				# Ok, it must be generic
				assert type(container) == datastructures.ModDateTrackingBTreeContainer
				assert container.__parent__ == ucontainers
				# These we need to replace
				new_cont = ucontainers.containerType()
				j = 0
				for ck, cv in container.items():
					if ck == 'Last Modified': continue
					j += 1
					new_cont[ck] = cv
				del ucontainers.containers[k]
				ucontainers.addContainer( k, new_cont )
				logger.debug( "Copied %d items from %s to %s on %s", j, k, new_cont, user.username )


		logger.debug( "Updated %d containers for %s", i, user.username )
