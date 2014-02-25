#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Generation 45 evolver

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 45

from zope import interface
from zope import component
from zope.component.hooks import site, setHooks

from zc import intid as zc_intid

from .install import install_metadata_catalog

from nti.dataserver.interfaces import IDataserver

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
	Evolve generation 44 to 45 by adding the general object metadata
	index.
	"""

	setHooks()
	ds_folder = context.connection.root()['nti.dataserver']
	mock_ds = MockDataserver(ds_folder, context.connection)
	gsm = component.getGlobalSiteManager()
	gsm.registerUtility(mock_ds)
	try:
		with site( ds_folder ):
			logger.info( "Installing catalog" )
			catalog = install_metadata_catalog( ds_folder, component.getUtility(zc_intid.IIntIds ) )
			catalog.updateIndexes()
			logger.info( "Done installing catalog")
	finally:
		gsm.unregisterUtility(mock_ds)
