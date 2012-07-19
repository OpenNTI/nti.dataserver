#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
zope.generations generation 16 evolver for nti.dataserver

$Id$
"""
from __future__ import print_function, unicode_literals

__docformat__ = 'restructuredtext'

generation = 16

logger = __import__('logging').getLogger( __name__ )

from zope.generations.utility import findObjectsMatching
from zope import interface


from nti.dataserver import enclosures
from nti.dataserver import interfaces as nti_interfaces

from nti.deprecated import hides_warnings

@hides_warnings
def evolve( context ):
	"""
	Evolve generation 15 to generation 16 by setting an interface on the root folder,
	and giving enclosures containers names.

	"""
	root = context.connection.root()
	dataserver_folder = root['nti.dataserver']
	interface.alsoProvides( dataserver_folder, nti_interfaces.IDataserverFolder )


	for mixin in findObjectsMatching( dataserver_folder, lambda x: isinstance(x, enclosures.SimpleEnclosureMixin) ):
		if mixin._enclosures is None:
			continue

		old_enc = mixin._enclosures
		# Force re-creation by deleting the existing, and then
		# re-adding any needed enclosures. This will reparent
		# everything nicely as well
		del mixin._enclosures

		for enc in old_enc.values():
			mixin.add_enclosure( enc )
