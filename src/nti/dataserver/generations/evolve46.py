#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Generation 46 evolver

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 46

from zope import interface
from zope import component
from zope.catalog.interfaces import ICatalog
from zope.component.hooks import site, setHooks

import BTrees

from nti.dataserver.interfaces import IDataserver
from nti.dataserver.metadata_index import CATALOG_NAME

from ..metadata_index import LastModifiedIndex

@interface.implementer(IDataserver)
class MockDataserver(object):

	def __init__(self, dataserver_folder, root_connection):
		self.dataserver_folder = dataserver_folder
		self.root = dataserver_folder
		self.root_connection = root_connection
		self.users_folder = dataserver_folder['users']
		self.shards = dataserver_folder['shards']
		self.root_folder = dataserver_folder.__parent__

def evolve( context ):
	"""
	Evolve generation 45 to 46 by adding the lastModified
	index.
	"""

	setHooks()
	ds_folder = context.connection.root()['nti.dataserver']
	mock_ds = MockDataserver(ds_folder, context.connection)
	gsm = component.getGlobalSiteManager()
	gsm.registerUtility(mock_ds)

	try:
		with site( ds_folder ):
			logger.info( "Updating catalog" )
			catalog = component.getUtility(ICatalog, name=CATALOG_NAME)
			# This fires an event which triggers re-indexing
			if 'lastModified' not in catalog:
				catalog['lastModified'] = LastModifiedIndex(family=BTrees.family64)
			logger.info( "Done updating catalog")
	finally:
		gsm.unregisterUtility(mock_ds)
