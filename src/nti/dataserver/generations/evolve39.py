#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 39

from zope import component
from zope.component.hooks import site, setHooks

from zope.intid.interfaces import IIntIds

from ZODB.POSException import POSKeyError

from nti.dataserver.contenttypes.threadable import ThreadableMixin
from nti.dataserver.contenttypes.threadable import _threadable_added

def evolve( context ):
	"""
	Evolve generation 38 to generation 39 by building the reference counts 
	for threadable objects.
	"""
	setHooks()
	ds_folder = context.connection.root()['nti.dataserver']
	with site( ds_folder ):
		assert component.getSiteManager() == ds_folder.getSiteManager(), "Hooks not installed?"

		intids = component.getUtility(IIntIds)

		# Simply iterate linearly regardless of containment using the intid registry.
		# avoid directly calling 'items' as it builds a whole list
		updated = 0
		broken = 0
		total = 0
		for intid, item in intids.refs.items():
			total += 1
			try:
				# We will only see an item once. But if there are ContainedProxy
				# or other proxies, its possible we could get the same logical item
				# twice.
				# Also, but checking the type of the object, as opposed to an interface,
				# we avoid any unneeded calls to __setstate__
				if ThreadableMixin not in type(item).mro():
					continue
				_threadable_added( item, intids, intid )
				updated += 1
			except POSKeyError:
				# Broken object, usually a test condition
				broken += 1

		logger.debug( "Updated %s objects out of %s total/%s broken", 
					  updated, total, broken )

