#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Content search generation 28.

.. $Id$
"""
from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 30

from zope import component

from zope.component.hooks import site, setHooks

from nti.contentsearch.interfaces import IContentSearcher

def evolve(context):
	"""
	Evolve generation 29 to 30 by removing searchers registered in the
	root persistent site.
	"""
	setHooks()
	conn = context.connection
	root = conn.root()
	ds_folder = root['nti.dataserver']
	with site(ds_folder):
		sm = component.getSiteManager()
		for name, searcher in component.getUtilitiesFor(IContentSearcher):
			logger.info("Unregistering searcher %s = %r", name, searcher)
			sm.unregisterUtility(searcher,
								 provided=IContentSearcher,
								 name=name)
