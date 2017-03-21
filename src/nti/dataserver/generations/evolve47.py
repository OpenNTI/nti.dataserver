#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Generation 47 evolver

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 47

from zope.component.hooks import site, setHooks

from nti.site.hostpolicy import synchronize_host_policies

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
		try:
			install_sites_folder( ds_folder )
		except KeyError:
			# Because we ran with generation officially at 46
			# for awhile before going to 47, some brand new
			# databases might actually have one of these
			# in them. No biggie.
			pass

		synchronize_host_policies()
