#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 43

from zope.intid import IIntIds

from zope import component
from zope.catalog.interfaces import ICatalog
from zope.component.hooks import site, setHooks

import BTrees

from nti.dataserver.users import index as user_index

def evolve( context ):
	"""
	Evolve generation 42 to 43 by adding the realname_parts index
	and installing the new topic index.
	"""
	
	setHooks()
	ds_folder = context.connection.root()['nti.dataserver']
	with site( ds_folder ):
		assert component.getSiteManager() == ds_folder.getSiteManager(), "Hooks not installed?"

		intids = component.getUtility(IIntIds)
		ent_catalog = component.getUtility(ICatalog, name=user_index.CATALOG_NAME)
		
		for name, clazz in ( ('realname_parts', user_index.RealnamePartsIndex), ):
			index = clazz( family=BTrees.family64 )
			intids.register( index )
			# The ObjectAddedEvent must fire
			if name in ent_catalog:
				del ent_catalog[name]
			ent_catalog[name] = index

		opt_in_comm_index = user_index.TopicIndex( family=BTrees.family64 )
		opt_in_comm_set = user_index.OptInEmailCommunicationFilteredSet('opt_in_email_communication',
																		 family=BTrees.family64 )
		opt_in_comm_index.addFilter( opt_in_comm_set )
		intids.register( opt_in_comm_index )
		if 'topics' in ent_catalog:
			del ent_catalog['topics']
		ent_catalog['topics'] = opt_in_comm_index
