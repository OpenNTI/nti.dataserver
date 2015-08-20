#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 66

from zope import interface

from zope.component.hooks import setHooks

from nti.dataserver.interfaces import IUsersFolder

def do_evolve(context, generation=generation):
	setHooks()
	conn = context.connection
	root = conn.root()
	dataserver_folder = root['nti.dataserver']
	users_folder = dataserver_folder['users']
	interface.alsoProvides(users_folder, IUsersFolder)
	logger.info('Dataserver evolution %s done.', generation)

def evolve(context):
	"""
	Evolve to 66 by marking the users folder
	"""
	do_evolve(context, generation)
