#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Administration views.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from nti.contentlibrary.interfaces import IContentPackageLibrary
from nti.contentlibrary.interfaces import ISyncableContentPackageLibrary

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.dataserver.site import synchronize_host_policies
from nti.dataserver.site import run_job_in_all_host_sites
from nti.contentlibrary.subscribers import install_site_content_library


from pyramid.view import view_config

from nti.dataserver.authorization import ACT_COPPA_ADMIN

@view_config( route_name='objects.generic.traversal',
			  renderer='rest',
			  context='nti.dataserver.interfaces.IDataserverFolder',
			  request_method='POST',
			  permission=ACT_COPPA_ADMIN,
			  name='SyncAllLibraries') # XXX better permission
class _SyncAllLibrariesView(AbstractAuthenticatedView):
	"""
	A view that synchronizes all of the in-database libraries
	(and sites) with their on-disk and site configurations.

	.. note:: TODO: While this may be useful for scripts,
		we also need to write a pretty HTML page that shows
		the various sync stats, like time last sync'd, whether
		the directory is found, etc, and lets people sync
		from there.
	"""

	def __call__(self):

		# First, synchronize the policies, make sure everything is all nice and installed.
		synchronize_host_policies()

		# Next, the libraries.
		# NOTE: We do not synchronize the global library; it is not
		# expected to be persistent and is not shared across
		# instances, so synchronizing it now will actually cause
		# things to be /out/ of sync.
		# We just keep track of it to make sure we don't.
		seen = set()
		seen.add(None)
		global_lib = component.getGlobalSiteManager().queryUtility(IContentPackageLibrary)
		seen.add(global_lib)

		def sync_site_library():
			# Mostly for testing, if we started up with a different library
			# that could not provide valid site libraries, install
			# one if we can get there now.
			site_lib = install_site_content_library(component.getSiteManager())
			if site_lib in seen:
				return
			seen.add(site_lib)

			syncer = ISyncableContentPackageLibrary(site_lib, None)
			if syncer is not None:
				logger.info("Sync library %s", site_lib)
				return site_lib.syncContentPackages()

		results = run_job_in_all_host_sites(sync_site_library)
		return [x[1] for x in results]
