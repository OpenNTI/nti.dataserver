#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 77

from zope import component

from zope.component.hooks import site
from zope.component.hooks import setHooks

from zope.intid.interfaces import IIntIds

from zope.location import locate

from nti.recorder.index import IX_TYPE
from nti.recorder.index import IX_LOCKED
from nti.recorder.index import IX_MIMETYPE
from nti.recorder.index import IX_PRINCIPAL

from nti.recorder.index import TypeIndex
from nti.recorder.index import LockedIndex
from nti.recorder.index import MimeTypeIndex
from nti.recorder.index import get_recordables
from nti.recorder.index import install_recorder_catalog

from nti.recorder.interfaces import TRX_TYPE_UPDATE

IX_SITE = 'site'
IX_TARGET_INTID = 'targetIntId'

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
		if IX_MIMETYPE not in catalog:
			index = MimeTypeIndex(family=intids.family)
			locate(index, catalog, IX_MIMETYPE)
			intids.register(index)
			catalog[IX_MIMETYPE] = index

			for recordable in get_recordables(catalog=catalog, intids=intids):
				doc_id = intids.queryId(recordable)
				if doc_id is not None:
					index.index_doc(doc_id, recordable)

		if IX_LOCKED not in catalog:
			index = LockedIndex(family=intids.family)
			locate(index, catalog, IX_LOCKED)
			intids.register(index)
			catalog[IX_LOCKED] = index

			for recordable in get_recordables(catalog=catalog, intids=intids):
				doc_id = intids.queryId(recordable)
				if doc_id is not None:
					index.index_doc(doc_id, recordable)

		if IX_TYPE not in catalog:
			type_index = TypeIndex(family=intids.family)
			intids.register(type_index)
			locate(type_index, catalog, IX_TYPE)
			catalog[IX_TYPE] = type_index

			prin_index = catalog[IX_PRINCIPAL].index
			for doc_id in prin_index.documents_to_values.keys():
				type_index.index_doc(doc_id, TRX_TYPE_UPDATE)

		if IX_TARGET_INTID in catalog:
			index = catalog[IX_TARGET_INTID]
			intids.unregister(index)
			del catalog[IX_TARGET_INTID]
			locate(index, None, None)
			index.clear()

		if IX_SITE in catalog:
			old_idx = catalog[IX_SITE]
			intids.unregister(old_idx)
			del catalog[IX_SITE]
			locate(old_idx, None, None)
			# should be empty since the catalog is a metadata catalog
			# as such access to the site data is not possible
			old_idx.clear()

		logger.info('Dataserver evolution %s done.', generation)

def evolve(context):
	"""
	Evolve to gen 77 by modifying the recorder catalog.
	"""
	do_evolve(context)
