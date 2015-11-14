#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 72

from zope import component

from zope.component.hooks import site
from zope.component.hooks import setHooks

from zope.intid.interfaces import IIntIds

from zope.location import locate

from nti.recorder.index import install_recorder_catalog

IX_SITE = 'site'

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
		
		if IX_SITE in catalog:
			old_idx = catalog[IX_SITE]
			intids.unregister(old_idx)
			del catalog[IX_SITE]
			locate(old_idx, None, None)
			# should be empty since the catalog is a metadata catalog
			# as such access to the site data is not possible
			old_idx.clear()
		logger.info('Dataserver evolution %s done.', generation)

def evolve(context):
	"""
	Evolve to gen 72 by removing the site index from the recorder catalog
	"""
	do_evolve(context)
