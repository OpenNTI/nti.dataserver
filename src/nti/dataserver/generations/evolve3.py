#!/usr/bin/env python
"""zope.generations generation 3 evolver for nti.dataserver
$Id$
"""
from __future__ import print_function, unicode_literals

__docformat__ = 'restructuredtext'

generation = 3

from zope.generations.utility import findObjectsMatching

from nti.dataserver import users, datastructures
from BTrees.OOBTree import OOTreeSet

def evolve( context ):
	"""
	Evolve generation 2 to generation 3 by changing all users to have the correct
	muting structure.
	"""
	for self in findObjectsMatching( context.connection.root(), lambda x: isinstance(x,users.SharingTarget) ):
		# For muted conversations, which can be unmuted, there is an
		# identical structure. References are moved in and out of this
		# container as conversations are un/muted. The goal of this structure
		# is to keep reads fast. Only writes--changing the muted status--are slow
		self.containers_of_muted = datastructures.ContainedStorage( weak=True,
																   create=False,
																   containerType=datastructures.PersistentExternalizableList,
																   set_ids=False )
		# This maintains the OIDs whose conversations are muted.
		self.muted_oids = OOTreeSet()
