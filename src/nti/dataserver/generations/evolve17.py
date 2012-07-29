#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
zope.generations generation 17 evolver for nti.dataserver

$Id$
"""
from __future__ import print_function, unicode_literals

__docformat__ = 'restructuredtext'

generation = 17

logger = __import__('logging').getLogger( __name__ )

from zope.generations.utility import findObjectsMatching

from BTrees.OOBTree import OOBTree
import zc.intid
from zope import component
from nti.dataserver import datastructures
from nti.dataserver.generations.install import install_intids
from nti.dataserver.chat_transcripts import _MeetingTranscriptStorage as MTS

from zope.container.contained import getProxiedObject

def evolve( context ):
	"""
	Evolve generation 16 to generation 17 by:

	#. Registering an intid utility with the site manager.
	#. Giving all entities (user, provider, community) intids.
	#. Giving all data created by users intids. (Incidentally, removing any useless proxies.)
	#. Dropping all existing transcript storage; they aren't accessible from the app anyway right now.
	#. Changing all shared data from direct/weak references to intids, including the stream cache.

	"""
	root = context.connection.root()
	dataserver_folder = root['nti.dataserver']

	intids = dataserver_folder.getSiteManager().queryUtility( zc.intid.IIntIds )
	if intids is None:
		intids = install_intids( dataserver_folder ) # 1. (idempotent)
	# We're not running in a site, and, as we're called as a subscriber,
	# in the current components, we can't use the hook to change out the
	# site (?)
	component.provideUtility( intids, provides=zc.intid.IIntIds )


	for type_ in ('users', 'providers'):
		for user in dataserver_folder[type_].values():
			__traceback_info__ = type_, user
			intids.register( user ) # 2. (idempotent)


			reg_count = 0
			reg_drop_count = 0
			to_drop = []
			to_re_add = []
			for container in user.containers.values() if hasattr(user, 'containers') else (): # 3. (idempotent)
				for obj in container.values():
					__traceback_info__ = type_, user, container, obj
					if isinstance( obj, float ): #pragma: no cover
						pass
					elif isinstance( obj, MTS ):
						to_drop.append( obj )
					# change contained proxies to the real object
					elif getProxiedObject( obj ) is not obj: # pragma: no cover
						# hard to test this because of the constraints that prevent getting
						# proxies into storage nowadays
						to_drop.append( obj )
						prox_obj = getProxiedObject( obj )
						datastructures.check_contained_object_for_storage( prox_obj )
						to_re_add.append( prox_obj )
						intids.register( prox_obj )
						reg_count += 1
					else:
						intids.register( obj )
						reg_count += 1


			for obj in to_drop: # 4. (idempotent)
				user.deleteContainedObject( obj.containerId, obj.id )

			if to_re_add:
				user.containers.afterAddContainedObject = lambda *args: False
				for obj in to_re_add:
					user.addContainedObject( obj )


			reg_drop_count = len(to_drop)
			# 5. (idempotent)
			if not isinstance( user.__dict__.get( 'streamCache' ), OOBTree ):
				continue

			# Copy the old values, and clear them out.
			# This lets the new properties automatically take over
			stream_cache = user.__dict__['streamCache']
			sharedCont = user.__dict__['containersOfShared']
			mutedCont = user.__dict__['containers_of_muted']

			del user.streamCache
			del user.containersOfShared
			del user.containers_of_muted

			count = 0
			drop_count = 0
			for plist in stream_cache.values():
				if isinstance( plist, float ): #pragma: no cover
					continue
				for change in plist:
					if change is None:
						# Weak ref, gone missing
						drop_count += 1
						continue
					# Order is unpredictable between the owner and the target,
					# so we need to register this too
					intids.register( change.object )
					user.streamCache.addContainedObject( change )
					count += 1

			for the_old_cont, the_name in ((sharedCont, 'containersOfShared'), (mutedCont,'containers_of_muted')):
				new_cont = getattr( user, the_name )
				__traceback_info__ = user, the_name, the_old_cont, the_old_cont.containers, the_name
				if 'Last Modified' in the_old_cont.containers: #pragma: no cover
					# Old containers that happened to use the ModDateTrackingBTree
					the_old_cont.containers = dict( the_old_cont.containers )
					the_old_cont.containers.pop( 'Last Modified' )
				for contained_obj in the_old_cont.iter_all_contained_objects():
					# These will be weak refs we need to unwrap
					__traceback_info__ = user, the_name, contained_obj
					contained_obj = contained_obj()
					if contained_obj is None:
						drop_count += 1
						continue
					__traceback_info__ = user, the_name, contained_obj
					intids.register( contained_obj )
					new_cont.addContainedObject( contained_obj )
					count += 1

			logger.debug( "Registered %d/%d owned and migrated %d/%d shared objects for %s", reg_count, reg_count + reg_drop_count, count, count + drop_count, user )
