#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 60

import functools

from zope import component
from zope import interface

from zope.annotation.interfaces import IAnnotations

from zope.component.hooks import site, setHooks

from zope.intid.interfaces import IIntIds

from nti.app.contentlibrary.synchronize.subscribers import _update_indices_when_content_changes

from nti.contentlibrary.indexed_data.index import NTIIDIndex
from nti.contentlibrary.indexed_data.index import install_container_catalog

from nti.contentlibrary.indexed_data.interfaces import CONTAINER_IFACES
from nti.contentlibrary.indexed_data.interfaces import TAG_NAMESPACE_FILE

from nti.contentlibrary.interfaces import IContentPackageLibrary

from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IOIDResolver

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

def _drop_annotation(unit, iface):
	key = 'nti.contentlibrary.indexed_data.container.IndexedDataContainer'
	namespace = iface.queryTaggedValue(TAG_NAMESPACE_FILE, '')
	if namespace:
		key = key + '_' + namespace
	annotations = IAnnotations(unit)
	annotations.data.pop(key, None)

def _drop_annotations_for_unit(unit):
	"""
	Recursively remove annotation for the given unit and children.
	"""
	for iface in CONTAINER_IFACES:
		_drop_annotation(unit, iface)
	for child in unit.children:
		_drop_annotations_for_unit(child)

def index_library(intids):
	library = component.queryUtility(IContentPackageLibrary)
	if library is not None:
		logger.info('Migrating library (%s)', library)
		for package in library.contentPackages:
			uid = intids.queryId(package)
			if uid is not None:
				logger.info('Indexing (%s)', package)
				_drop_annotations_for_unit(package)
				_update_indices_when_content_changes(package, None)

def do_evolve(context):
	setHooks()
	conn = context.connection
	root = conn.root()
	ds_folder = root['nti.dataserver']

	mock_ds = MockDataserver()
	mock_ds.root = ds_folder
	component.provideUtility(mock_ds, IDataserver)

	with site(ds_folder):
		assert	component.getSiteManager() == ds_folder.getSiteManager(), \
				"Hooks not installed?"

		lsm = ds_folder.getSiteManager()
		intids = lsm.getUtility(IIntIds)

		catalog = install_container_catalog(ds_folder, intids)

		if not hasattr(catalog, '_ntiid_index'):
			catalog._ntiid_index = NTIIDIndex(family=intids.family)

		if not hasattr(catalog, '_last_modified'):
			catalog._last_modified = intids.family.OI.BTree()

		# load library
		library = component.queryUtility(IContentPackageLibrary)
		if library is not None:
			library.syncContentPackages()

		index_library(intids)
		run_job_in_all_host_sites(functools.partial(index_library, intids))

		logger.info('Dataserver evolution %s done.', generation)

def evolve(context):
	"""
	Migrate our index.json files from annotations to our catalog.
	"""
	do_evolve(context)
