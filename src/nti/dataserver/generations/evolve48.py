#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Generation 48 evolver

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 48

from zope import component
from zope.catalog.interfaces import ICatalog
from zope.component.hooks import site, setHooks

import BTrees

from nti.dataserver.metadata_index import CATALOG_NAME

from ..metadata_index import TP_DELETED_PLACEHOLDER
from ..metadata_index import DeletedObjectPlaceholderExtentFilteredSet

from .evolve45 import MockDataserver

def evolve( context ):
	"""
	Evolve generation 47 to 48 by adding the
	deleted object index.
	"""

	setHooks()
	ds_folder = context.connection.root()['nti.dataserver']
	mock_ds = MockDataserver(ds_folder, context.connection)
	gsm = component.getGlobalSiteManager()
	gsm.registerUtility(mock_ds)

	try:
		with site( ds_folder ):
			logger.info( "Updating placeholders" )

			catalog = component.getUtility(ICatalog, name=CATALOG_NAME)
			index = catalog['topics']
			deleted_set = DeletedObjectPlaceholderExtentFilteredSet(TP_DELETED_PLACEHOLDER)
			assert deleted_set.family is BTrees.family64
			index.addFilter(deleted_set)
			
			# Slightly faster to just re-index in this one filter
			for uid, obj in catalog._visitSublocations():
				deleted_set.index_doc(uid, obj)

			logger.info( "Done updating placeholders")
	finally:
		gsm.unregisterUtility(mock_ds)
