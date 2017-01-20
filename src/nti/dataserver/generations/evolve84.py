#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 84

from zope import component

from zope.component.hooks import site
from zope.component.hooks import setHooks

from zope.catalog.interfaces import ICatalog

from zope.intid.interfaces import IIntIds

from zope.index.topic import TopicIndex

from zope.index.topic.interfaces import ITopicFilteredSet

from zc.catalog.interfaces import IIndexValues

from nti.dataserver.metadata_index import IX_CREATOR

from nti.metadata import metadata_queue
from nti.metadata import dataserver_metadata_catalog

from nti.zope_catalog.interfaces import IKeywordIndex


def do_evolve(context):
	setHooks()
	conn = context.connection
	root = conn.root()
	ds_folder = root['nti.dataserver']

	with site(ds_folder):
		assert  component.getSiteManager() == ds_folder.getSiteManager(), \
				"Hooks not installed?"

		queue = metadata_queue()
		if queue is None:
			return

		lsm = ds_folder.getSiteManager()
		intids = lsm.getUtility(IIntIds)
		
		rest_ids = set()
		creator_ids = set()
		creator_index = dataserver_metadata_catalog()[IX_CREATOR]
		for name, catalog in list(component.getUtilitiesFor(ICatalog)):
			if not hasattr(catalog, "values"): # invalid catalog
				obj = lsm.queryUtility(provided=ICatalog, name=name)
				if intids.queryId(obj) is not None:
					intids.unregister(obj)
				lsm.unregisterUtility(obj, provided=ICatalog, name=name)
				continue

			for index in catalog.values():
				if index is creator_index:
					s = creator_ids
				else:
					s = rest_ids

				if IIndexValues.providedBy(index):
					s.update(index.ids())
				elif IKeywordIndex.providedBy(index):
					s.update(index.ids())
				elif isinstance(index, TopicIndex):
					for filter_index in index._filters.values():
						if ITopicFilteredSet.providedBy(filter_index):
							s.update(filter_index.getIds())

		# index difference
		for uid in rest_ids.difference(creator_ids):
			try:
				queue.add(uid)
			except TypeError:
				pass

		logger.info('Dataserver evolution %s done.', generation)


def evolve(context):
	"""
	Evolve to gen 84 by reindexing the missing creators
	"""
	do_evolve(context)
