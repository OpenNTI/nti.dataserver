#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 89

from zope import component

from zope.component.hooks import site
from zope.component.hooks import setHooks

from zope.intid.interfaces import IIntIds

from nti.contentfolder.index import install_content_resources_catalog


def do_evolve(context):
	setHooks()
	conn = context.connection
	root = conn.root()
	ds_folder = root['nti.dataserver']

	with site(ds_folder):
		assert	component.getSiteManager() == ds_folder.getSiteManager(), \
				"Hooks not installed?"

		lsm = ds_folder.getSiteManager()
		intids = lsm.getUtility(IIntIds)
		install_content_resources_catalog(ds_folder, intids)

	logger.info('Dataserver evolution %s done.', generation)

def evolve(context):
	"""
	Evolve to gen 89 by registering the content resources catalog
	"""
	do_evolve(context)
