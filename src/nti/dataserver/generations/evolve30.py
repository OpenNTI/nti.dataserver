#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Generation 30 evolver, which adds the user catalog.

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 30

from zope import component
from zope.component.hooks import site, setHooks

from zc import intid as zc_intid

from .install import install_user_catalog

def evolve( context ):
	"""
	Evolve generation 29 to generation 30 by adding the user catalog.
	"""

	setHooks()
	ds_folder = context.connection.root()['nti.dataserver']
	with site( ds_folder ):
		logger.info( "Installing catalog" )
		catalog = install_user_catalog( ds_folder, component.getUtility(zc_intid.IIntIds ) )
		catalog.updateIndexes()
		logger.info( "Done installing catalog")
