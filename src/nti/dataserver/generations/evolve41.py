#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 41

from zope.site.site import SiteManagementFolder

def evolve(context):
	"""
	Evolves from 40 to 41 by fixing up the site containment
	hierarchy to more closely match what's expected.
	"""

	# Our root folder's SiteManager should have the 'default' subfolder, that's
	# expected...depending on when it was created, it may or may not exist
	root_folder = context.connection.root()['nti.dataserver_root']
	if 'default' not in root_folder.getSiteManager():
		root_folder.getSiteManager()['default'] = SiteManagementFolder()

	# The root folder's SiteManager should have a proper parent
	root_folder.getSiteManager().__parent__ = root_folder

	# The dataserver folder's LSM has the wrong parent
	# and base site manager
	ds_folder = root_folder['dataserver2']
	ds_folder.getSiteManager().__parent__ = ds_folder
	ds_folder.getSiteManager().__bases__ = (root_folder.getSiteManager(),)

	# The application alias is missing
	context.connection.root()['Application'] = root_folder
