#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Generation 31 evolver

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 31

from zope import component
from zope.component.hooks import site, setHooks

from zc import intid as zc_intid

from .install import install_user_catalog

def evolve( context ):
	"""
	Evolve generation 30 to generation 31 by updating the user catalog with new indexes.
	"""

	setHooks()
	ds_folder = context.connection.root()['nti.dataserver']
	with site( ds_folder ):
		logger.info( "Installing catalog" )
		catalog = install_user_catalog( ds_folder, component.getUtility(zc_intid.IIntIds ) )
		catalog.updateIndexes()
		logger.info( "Done installing catalog")
