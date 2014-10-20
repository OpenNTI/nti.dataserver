# -*- coding: utf-8 -*-
"""
schema generation installation.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 51

import zope.intid

from zope import component
from zope.component.hooks import site, setHooks

from zope.catalog.interfaces import ICatalog

from nti.dataserver.metadata_index import CATALOG_NAME

from nti.metadata.queue import MetadataQueue

from nti.zope_catalog.interfaces import IMetadataCatalog
# FIXME Only in nti.metadata?
from nti.metadata.interfaces import IMetadataQueue

def do_evolve(context):
	setHooks()
	conn = context.connection
	root = conn.root()
	ds_folder = root['nti.dataserver']

	lsm = ds_folder.getSiteManager()
	intids = lsm.getUtility(zope.intid.IIntIds)

	with site(ds_folder):
		assert	component.getSiteManager() == ds_folder.getSiteManager(), \
				"Hooks not installed?"

		# Register our queue
		queue = MetadataQueue()
		queue.__parent__ = ds_folder
		queue.__name__ = '++etc++metadata++queue'
		intids.register(queue)
		lsm.registerUtility(queue, provided=IMetadataQueue)

		# Unregister and re-register under our new interface.
		# Our install script should not have to change.
		# Existing catalog consumers should not have to change.
		# We should also not need downtime.
		old_catalog = lsm.getUtility(provided=ICatalog, name=CATALOG_NAME)
		lsm.unregisterUtility( old_catalog, provided=ICatalog, name=CATALOG_NAME )
		lsm.registerUtility( old_catalog, provided=IMetadataCatalog, name=CATALOG_NAME )

		logger.info( 'nti.dataserver evolve51 complete.' )
		return

def evolve(context):
	do_evolve(context)

