#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 30

from zope import component

from zope.component.hooks import site, setHooks

from nti.contentsearch.interfaces import IContentSearcher

def do_evolve(context, generation=generation):
	setHooks()
	conn = context.connection
	ds_folder = conn.root()['nti.dataserver']
	with site(ds_folder):
		assert 	component.getSiteManager() == ds_folder.getSiteManager(), \
				"Hooks not installed?"

		sm = component.getSiteManager()
		for name, searcher in component.getUtilitiesFor(IContentSearcher):
			logger.info("Unregistering searcher %s = %r", name, searcher)
			sm.unregisterUtility(searcher,
								 provided=IContentSearcher,
								 name=name)

	logger.info('Evolution %s done', generation)

def evolve(context):
	"""
	Evolve generation 30 by removing searchers registered in the root persistent site.
	"""
	do_evolve(context)
