#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 58

from zope import component
from zope.intid.interfaces import IIntIds
from zope.component.hooks import site, setHooks
from nti.contentlibrary.indexed_data.index import install_container_catalog

def do_evolve(context):
	setHooks()
	conn = context.connection
	root = conn.root()
	ds_folder = root['nti.dataserver']

	with site(ds_folder):
		assert	component.getSiteManager() == ds_folder.getSiteManager(), \
				"Hooks not installed?"
		intids = component.getUtility(IIntIds)
		install_container_catalog(ds_folder, intids)

		logger.info('Dataserver evolution %s done.', generation)

def evolve(context):
	"""
	Add a container index, which indexes contained objects to their
	containers and types.
	"""
	do_evolve(context)
