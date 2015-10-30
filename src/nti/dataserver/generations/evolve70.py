#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 70

from zope import component

from zope.component.hooks import site
from zope.component.hooks import setHooks

from zope.intid.interfaces import IIntIds

from zope.location import locate

from nti.recorder.index import IX_LOCKED
from nti.recorder.index import LockedIndex
from nti.recorder.index import install_recorder_catalog

def do_evolve(context):
	setHooks()
	conn = context.connection
	root = conn.root()
	ds_folder = root['nti.dataserver']

	with site(ds_folder):
		assert  component.getSiteManager() == ds_folder.getSiteManager(), \
				"Hooks not installed?"

		lsm = ds_folder.getSiteManager()
		intids = lsm.getUtility(IIntIds)

		catalog = install_recorder_catalog(ds_folder, intids)
		if IX_LOCKED not in catalog:
			index = LockedIndex(family=intids.family)
			intids.register(index)
			locate(index, catalog, IX_LOCKED)
			catalog[IX_LOCKED] = index
		logger.info('Dataserver evolution %s done.', generation)

def evolve(context):
	"""
	Evolve to gen 70 by modifying the recorder catalog.
	"""
	do_evolve(context)
