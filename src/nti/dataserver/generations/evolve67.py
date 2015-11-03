#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 67

from functools import partial

from zope import component

from zope.intid.interfaces import IIntIds

from zope.component.hooks import site, setHooks, getSite

from nti.assessment.interfaces import IQAssessment

from nti.contentlibrary.indexed_data.index import SiteIndex
from nti.contentlibrary.indexed_data import IContainedObjectCatalog
from nti.contentlibrary.indexed_data.index import CATALOG_INDEX_NAME

from nti.contenttypes.presentation.interfaces import INTISlideDeck
from nti.contenttypes.presentation.interfaces import IPresentationAsset

from nti.site.hostpolicy import run_job_in_all_host_sites

def _index_assets(catalog, intids):
	sites = (getSite().__name__,)

	def _index_item(item):
		doc_id = intids.queryId(item)
		if doc_id is not None:
			catalog.site_index.index_doc(doc_id, sites)
			return True
		return False

	for _, item in component.getUtilitiesFor(IPresentationAsset):
		_index_item(item)
		if INTISlideDeck.providedBy(item):
			for slide in item.Slides or ():
				_index_item(slide)

			for video in item.Videos or ():
				_index_item(video)

	for _, item in component.getUtilitiesFor(IQAssessment):
		_index_item(item)

def do_evolve(context, generation=generation):
	setHooks()
	conn = context.connection
	root = conn.root()
	dataserver_folder = root['nti.dataserver']

	with site(dataserver_folder):
		assert	component.getSiteManager() == dataserver_folder.getSiteManager(), \
				"Hooks not installed?"

		lsm = dataserver_folder.getSiteManager()
		intids = lsm.getUtility(IIntIds)
		catalog = lsm.getUtility(IContainedObjectCatalog, name=CATALOG_INDEX_NAME)

		if not hasattr(catalog, "_site_index"):
			catalog._site_index = SiteIndex(family=intids.family)

		# index in GSM
		_index_assets(catalog, intids)

		# index in all sites
		run_job_in_all_host_sites(partial(_index_assets, catalog, intids))

		logger.info('Dataserver evolution %s done.', generation)

def evolve(context):
	"""
	Evolve to 67 by indexing the site for assets
	"""
	do_evolve(context, generation)
