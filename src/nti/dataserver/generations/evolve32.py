#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Generation 32 evolver

$Id: evolve32.py 13187 2012-10-13 18:29:28Z jason.madden $
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

generation = 32

from collections import Iterable

from zope.generations.utility import findObjectsMatching

from zope import component
from zope.component.hooks import site, setHooks
from nti.dataserver.contenttypes import Canvas

import logging
logger = logging.getLogger( __name__ )

def migrate( obj ):
	for _, item in enumerate(obj.body):
		if isinstance( item, Canvas ):
			if not hasattr(item, "viewPortRatio"):
				item.viewPortRatio = 1.0

def needs_migrate(x):
	"""
	Something needs migrated if it has an iterable 'body'. This catches
	Notes, the most common thing, but also the MessageInfo objects stored under
	annotations of users.
	"""
	return isinstance( getattr( x, 'body', None ), Iterable)

def evolve( context ):
	"""
	Evolve generation 31 to generation 32 by making adding a field called viewPortRatio
	to all cavas objects.
	"""

	setHooks()
	ds_folder = context.connection.root()['nti.dataserver']
	with site( ds_folder ):
		assert component.getSiteManager() == ds_folder.getSiteManager(), "Hooks not installed?"

		users = ds_folder['users']
		for user in users.values():
			for note in findObjectsMatching( user, needs_migrate):
				__traceback_info__ = user, note
				migrate( note )
