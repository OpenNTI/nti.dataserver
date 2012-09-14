#!/usr/bin/env python
"""
zope.generations generation 24 evolver for nti.dataserver

$Id$
"""
from __future__ import print_function, unicode_literals

__docformat__ = 'restructuredtext'

generation = 24

from zope.generations.utility import findObjectsMatching

from zope import component
from zope.component.hooks import site, setHooks
from persistent import Persistent
from collections import Iterable

from nti.dataserver import contenttypes
from nti.dataserver.contenttypes import Canvas

def _build_map():
	result = {}
	for k, v in contenttypes.__dict__.items():
		if k.startswith( 'Canvas' ) and k.endswith( 'Shape'):
			result[v] = contenttypes.__dict__['Nonpersistent' + k]
	return result

PERSISTENT_TO_NONPERSISTENT = _build_map()

def migrate( note ):
	for item in note.body:
		if isinstance( item, Canvas ):
			for i, shape in enumerate(item.shapeList):
				# If we find a persistent shape
				if isinstance( shape, Persistent ):
					# Make the same kind of non-persistent object
					new_shape = PERSISTENT_TO_NONPERSISTENT[type(shape)]()
					# and copy everything out of its dict. We know
					# these are all primitives
					shape._p_activate()
					for k, v in shape.__dict__.items():
						new_shape.__dict__[k] = v
					__traceback_info__ = shape, new_shape

					assert new_shape == shape

					# Finally, replace the object
					item.shapeList[i] = new_shape

	note._v_migrated = True

def needs_migrate(x):
	"""
	Something needs migrated if it has an iterable 'body'. This catches
	Notes, the most common thing, but also the MessageInfo objects stored under
	annotations of users.
	"""
	return isinstance( getattr( x, 'body', None ), Iterable) and not getattr( x, '_v_migrated', False )

def evolve( context ):
	"""
	Evolve generation 23 to generation 24 by making all CanvasShape objects
	non-persistent.
	"""

	setHooks()
	ds_folder = context.connection.root()['nti.dataserver']
	with site( ds_folder ):
		assert component.getSiteManager() == ds_folder.getSiteManager(), "Hooks not installed?"

		users = ds_folder['users']
		for user in users.values():
			for note in findObjectsMatching( user,
											 needs_migrate):
				__traceback_info__ = user, note
				migrate( note )
