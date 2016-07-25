#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 81

from zope import component

from zope.component.hooks import setHooks
from zope.component.hooks import site as current_site

from BTrees.OIBTree import OIBTree
from BTrees.OOBTree import OOBTree

from nti.site.hostpolicy import get_all_host_sites

from nti.site.interfaces import IHostPolicySiteManager

def do_evolve(context):
	setHooks()
	conn = context.connection
	root = conn.root()
	ds_folder = root['nti.dataserver']

	with current_site(ds_folder):
		assert  component.getSiteManager() == ds_folder.getSiteManager(), \
				"Hooks not installed?"

		for site in get_all_host_sites():
			manager = site.getSiteManager()
			if not IHostPolicySiteManager.providedBy(manager):
				continue	
			if 		hasattr(manager, "_utility_registrations")	\
				and not isinstance(manager._utility_registrations, OOBTree):					
				manager._utility_registrations = OOBTree(manager._utility_registrations)
				manager._adapter_registrations = OOBTree(manager._adapter_registrations)
			
			for name in ('adapters', 'utilities'):
				registry = getattr(manager, name, None)
				if 		hasattr(registry, "_provided")	\
					and not isinstance(registry._provided, OIBTree):
					registry._provided = OIBTree(registry._provided)
				
		logger.info('Dataserver evolution %s done.', generation)

def evolve(context):
	"""
	Evolve to gen 81 to update persistent local site mangager internals
	"""
	pass
	