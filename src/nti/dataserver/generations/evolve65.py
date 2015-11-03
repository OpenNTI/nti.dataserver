#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 65

import functools

from zope import component
from zope import interface

from zope.intid.interfaces import IIntIds

from zope.component.hooks import site, setHooks

from nti.contentlibrary.interfaces import IContentUnit
from nti.contentlibrary.interfaces import IContentPackageLibrary

from nti.contentlibrary.indexed_data import IContainedObjectCatalog
from nti.contentlibrary.indexed_data.index import CATALOG_INDEX_NAME

from nti.contenttypes.presentation.interfaces import INTISlideDeck
from nti.contenttypes.presentation.interfaces import IPresentationAsset
from nti.contenttypes.presentation.interfaces import IPresentationAssetContainer

from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IOIDResolver

from nti.ntiids.ntiids import find_object_with_ntiid

from nti.site.hostpolicy import run_job_in_all_host_sites

@interface.implementer(IDataserver)
class MockDataserver(object):

	root = None

	def get_by_oid(self, oid, ignore_creator=False):
		resolver = component.queryUtility(IOIDResolver)
		if resolver is None:
			logger.warn("Using dataserver without a proper ISiteManager configuration.")
		else:
			return resolver.get_object_by_oid(oid, ignore_creator=ignore_creator)
		return None

FILENAMES = ('audio_index.json', 'video_index.json',
			 'related_content_index.json', 'timeline_index.json',
			 'slidedeck_index.json')

def _store_asset(content_unit, container_id, ntiid, item):
	container = IPresentationAssetContainer(content_unit, None)
	if container is not None:
		container[ntiid] = item
		# check for slide decks
		if INTISlideDeck.providedBy(item):
			for slide in item.Slides or ():
				container[slide.ntiid] = slide

			for video in item.Videos or ():
				container[video.ntiid] = video
		return True
	return False

def _store_assets(intids, catalog, seen):
	result = 0
	library = component.queryUtility(IContentPackageLibrary)
	if library is None:
		return result

	logger.info('Scanning library (%s)', library)
	for name, item in component.getUtilitiesFor(IPresentationAsset):
		if name in seen:
			continue
		seen.add(name)
		containers = catalog.get_containers(item, intids)
		for container in containers or ():
			unit = find_object_with_ntiid(container)
			unit = IContentUnit(unit, None)
			if unit is not None and not unit.children and name not in container:
				_store_asset(unit, container, name, item)
				result += 1
	logger.info('%s asset(s) stored for library (%s)', result, library)
	return result

def do_evolve(context, generation=generation):
	setHooks()
	conn = context.connection
	root = conn.root()
	dataserver_folder = root['nti.dataserver']

	mock_ds = MockDataserver()
	mock_ds.root = dataserver_folder
	component.provideUtility(mock_ds, IDataserver)

	with site(dataserver_folder):
		assert	component.getSiteManager() == dataserver_folder.getSiteManager(), \
				"Hooks not installed?"

		lsm = dataserver_folder.getSiteManager()
		intids = lsm.getUtility(IIntIds)
		catalog = lsm.getUtility(IContainedObjectCatalog, name=CATALOG_INDEX_NAME)

		# Load library
		library = component.queryUtility(IContentPackageLibrary)
		if library is not None:
			library.syncContentPackages()
			
		seen = set()
		_store_assets(intids, catalog, seen)
		run_job_in_all_host_sites(functools.partial(_store_assets, intids, catalog, seen))
		logger.info('Dataserver evolution %s done.', generation)

def evolve(context):
	"""
	Evolve to 65 by storing presentation assets in content units
	"""
	do_evolve(context, generation)
