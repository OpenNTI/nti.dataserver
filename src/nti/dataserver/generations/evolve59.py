#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 59

from zope import component
from zope.component.hooks import site, setHooks

from nti.contentlibrary.indexed_data import get_catalog

def do_evolve(context):
	setHooks()
	conn = context.connection
	root = conn.root()
	ds_folder = root['nti.dataserver']

	with site(ds_folder):
		assert	component.getSiteManager() == ds_folder.getSiteManager(), \
				"Hooks not installed?"

		catalog = get_catalog()
		catalog.reset()
		logger.info('Dataserver evolution %s done.', generation)

def evolve(context):
	"""
	Reset the content library catalog to add a new index; should only affect dev.
	"""
	do_evolve(context)
