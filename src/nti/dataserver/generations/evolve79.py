#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 79

from zope import component

from zope.component.hooks import site
from zope.component.hooks import setHooks

from zope.intid.interfaces import IIntIds

from zope.location.location import locate

from nti.dataserver.users.index import IX_MIMETYPE
from nti.dataserver.users.index import MimeTypeIndex
from nti.dataserver.users.index import install_entity_catalog

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

		catalog = install_entity_catalog(ds_folder, intids)
		if IX_MIMETYPE not in catalog:
			index = MimeTypeIndex(family=intids.family)
			intids.register(index)
			locate(index, catalog, IX_MIMETYPE)
			catalog[IX_MIMETYPE] = index
			
			users = ds_folder['users']
			for user in users.values():
				doc_id = intids.queryId(user)
				if doc_id is not None:
					index.index_doc(doc_id, user)

		logger.info('Dataserver evolution %s done.', generation)

def evolve(context):
	"""
	Evolve to gen 79 by installing the mimeType index for the entity catalog
	"""
	do_evolve(context)
