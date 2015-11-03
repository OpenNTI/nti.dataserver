#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 42

from zope import component
from zope.component.hooks import site, setHooks

import BTrees

from zope.catalog.interfaces import ICatalog

from nti.dataserver.users import index as user_index

def evolve( context ):
	"""
	Evolve generation 41 to 42 by fixing the user ICatalog's family.

	Older versions of the installer failed to set the family of the
	catalog appropriately, leaving it to be family32 (the default).
	This means that its apply() method won't work, as each of the
	field indexes is created with family64.

	"""
	setHooks()
	ds_folder = context.connection.root()['nti.dataserver']
	with site( ds_folder ):
		assert component.getSiteManager() == ds_folder.getSiteManager(), "Hooks not installed?"

		ent_catalog = component.getUtility(ICatalog, name=user_index.CATALOG_NAME)
		ent_catalog.family = BTrees.family64
