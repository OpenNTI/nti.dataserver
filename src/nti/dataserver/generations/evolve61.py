#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 61

from zope.component.hooks import setHooks

from zope.intid.interfaces import IIntIds

from nti.contentlibrary.indexed_data.index import NTIIDIndex
from nti.contentlibrary.indexed_data import CATALOG_INDEX_NAME
from nti.contentlibrary.indexed_data.interfaces import IContainedObjectCatalog

from nti.zope_catalog.catalog import ResultSet

def do_evolve(context):
	setHooks()
	conn = context.connection
	root = conn.root()

	dataserver_folder = root['nti.dataserver']
	lsm = dataserver_folder.getSiteManager()
	intids = lsm.getUtility(IIntIds)

	catalog = lsm.getUtility(IContainedObjectCatalog, name=CATALOG_INDEX_NAME)
	if hasattr(catalog, '_ntiid_index'):
		return # process done
	
	catalog._ntiid_index = NTIIDIndex(family=intids.family)
	docs_ids = catalog._type_index.documents_to_values.keys()
	for doc_id, value in ResultSet(docs_ids, intids, True).iter_pairs():
		catalog._ntiid_index.index_doc(doc_id, value)
	logger.info('Dataserver evolution %s done.', generation)
	
def evolve(context):
	"""
	Evolve to generation 61 by adding an index to the library index catalog
	"""
	do_evolve(context)
