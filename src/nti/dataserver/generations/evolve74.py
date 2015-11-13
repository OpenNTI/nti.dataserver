#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 74

from zope import component

from zope.component.hooks import site
from zope.component.hooks import setHooks

from zope.intid.interfaces import IIntIds

from zope.location import locate

from nti.recorder.index import IX_TYPE
from nti.recorder.index import IX_PRINCIPAL

from nti.recorder.index import TypeIndex
from nti.recorder.index import install_recorder_catalog

from nti.recorder.interfaces import TRX_TYPE_UPDATE

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
		if IX_TYPE not in catalog:
			type_index = TypeIndex(family=intids.family)
			intids.register(type_index)
			locate(type_index, catalog, IX_TYPE)
			catalog[IX_TYPE] = type_index
			
			# add values
			prin_index = catalog[IX_PRINCIPAL].index
			for doc_id in prin_index.documents_to_values.keys():
				type_index.index_doc(doc_id, TRX_TYPE_UPDATE)
	
		logger.info('Dataserver evolution %s done.', generation)

def evolve(context):
	"""
	Evolve to gen 74 by modifying the recorder catalog.
	"""
	do_evolve(context)
