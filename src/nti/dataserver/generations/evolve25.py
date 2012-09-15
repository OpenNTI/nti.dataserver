#!/usr/bin/env python
"""
zope.generations generation 25 evolver for nti.dataserver

$Id$
"""
from __future__ import print_function, unicode_literals

__docformat__ = 'restructuredtext'

generation = 25

from zope.generations.utility import findObjectsMatching

from zope import component
from zope.component.hooks import site, setHooks
from persistent.list import PersistentList
from collections import Iterable
import base64

from . import evolve24
from nti.dataserver.contenttypes import Canvas
from nti.dataserver.contenttypes.canvas import _CanvasUrlShape



def migrate( note ):
	evolve24.migrate( note ) # Be sure they are non-persistent
	for j, item in enumerate(note.body):
		if isinstance( item, Canvas ):

			if item.__parent__ is None:
				item.__parent__ = note
				item.__name__ = unicode( j )

			for i, shape in enumerate(item.shapeList):
				if shape.__parent__ is None:
					shape.__parent__ = item
					shape.__name__ = unicode( i )

				# If we find a url shape
				if isinstance( shape, _CanvasUrlShape ):
					try:
						shape._p_activate()
					except AttributeError: pass
					state = shape.__dict__
					if '_head' in state:
						# Something like: data:image/gif;base64
						item._p_changed = True
						head = state.pop( '_head' )
						raw_tail = state.pop( '_raw_tail' )

						data_url = head + ',' + base64.b64encode( raw_tail )
						shape.url = data_url

				if not isinstance( item.shapeList, PersistentList ):
					item.shapeList = PersistentList( item.shapeList )


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
	Evolve generation 24 to generation 25 by making all CanvasUrlShape objects
	have blob data, and setting the parent relationships between canvas objects, shapes,
	and their container.
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
