#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 62

import functools

from zope import component
from zope import interface

from zope.annotation.interfaces import IAnnotations

from zope.intid.interfaces import IIntIds

from zope.component.hooks import site, setHooks

from nti.contentlibrary.indexed_data import get_catalog
from nti.contentlibrary.indexed_data.index import NTIIDIndex
from nti.contentlibrary.interfaces import IContentPackageLibrary

from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IOIDResolver

from nti.site.hostpolicy import run_job_in_all_host_sites

from nti.zodb.containers import time_to_64bit_int

LM_KEY = 'nti.contentlibrary.indexed_data.LastModified'

def _get_lm_key( index_filename ):
	key = LM_KEY
	if index_filename:
		key = key + '_' + index_filename
	return key

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

def _drop_annotation( unit, filename ):
	annotes = IAnnotations( unit, None )
	key = _get_lm_key( filename )
	if annotes:
		return annotes.data.pop( key, None )

FILENAMES = ('audio_index.json',
			'video_index.json',
			'related_content_index.json',
			'timeline_index.json',
			'slidedeck_index.json')

def _index_library( intids ):
	catalog = get_catalog()
	catalog._ntiid_index = NTIIDIndex(family=intids.family)

	library = component.queryUtility( IContentPackageLibrary )
	if library is not None:
		logger.info( 'Migrating library (%s)', library )
		for package in library.contentPackages:
			uid = intids.queryId( package )
			if uid is not None:
				for filename in FILENAMES:
					last_mod = _drop_annotation( package, filename )
					if last_mod is not None:
						last_mod = time_to_64bit_int( last_mod )
						namespace = '%s.%s.LastModified' % ( package.ntiid, filename )
						catalog.set_last_modified( namespace, last_mod )

def do_evolve(context):
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
		catalog = get_catalog()
		if hasattr(catalog, '_last_modified'):
			return
		
		catalog._last_modified = intids.family.OI.BTree()

		# Load library
		library = component.queryUtility(IContentPackageLibrary)
		if library is not None:
			library.syncContentPackages()

		_index_library( intids )
		run_job_in_all_host_sites(functools.partial(_index_library, intids))
		logger.info('Dataserver evolution %s done.', generation)

def evolve(context):
	"""
	Evolve to 62 by moving last mod from annotations to index, allowing
	us to track global, non-persistent packages.
	"""
	do_evolve(context)
