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

import BTrees

from zope import component
from zope.component.hooks import site, setHooks

from zope.catalog.interfaces import ICatalog

from nti.dataserver.metadata_index import CATALOG_NAME
from nti.dataserver.metadata_index import MetadataCatalog

from nti.zope_catalog.interfaces import IMetadataCatalog

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

		# Unregister our old metadata index
		old_catalog = lsm.getUtility(provided=ICatalog, name=CATALOG_NAME)
		intids.unregister(old_catalog)
		lsm.unregisterUtility( old_catalog, provided=ICatalog, name=CATALOG_NAME )
		old_catalog.__parent__ = None

		# Add our new catalog
		new_catalog = MetadataCatalog( family=BTrees.family64 )
		new_catalog.__parent__ = ds_folder
		new_catalog.__name__ = CATALOG_NAME
		intids.register(new_catalog)
		lsm.registerUtility(new_catalog, provided=IMetadataCatalog, name=CATALOG_NAME)

		# Migrate indexes
		for k, v in old_catalog.items():
			# Fires re-index event...
			#new_catalog[k] = v
			new_catalog._setitemf( k, v )

		logger.info( 'nti.dataserver evolve51 complete.' )
		return

def evolve(context):
	do_evolve(context)

