#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Generation 31 evolver

$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 31


from zope.component.hooks import site, setHooks

from .install import install_sites_folder

def evolve( context ):
	"""
	Evolve generation 46 to generation 47 by
	installing the sites container.
	"""

	setHooks()
	ds_folder = context.connection.root()['nti.dataserver']
	with site( ds_folder ):
		logger.info( "Installing sites folder" )
		install_sites_folder( ds_folder )
