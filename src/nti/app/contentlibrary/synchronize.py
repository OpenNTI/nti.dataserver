#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import gc
import time

import gevent

from zope import component
from zope.event import notify

from zope.traversing.interfaces import IEtcNamespace

from nti.contentlibrary.interfaces import IContentPackageLibrary
from nti.contentlibrary.interfaces import ISyncableContentPackageLibrary
from nti.contentlibrary.interfaces import AllContentPackageLibrariesDidSyncEvent

from nti.contentlibrary.subscribers import install_site_content_library

from nti.site.hostpolicy import run_job_in_all_host_sites
from nti.site.hostpolicy import synchronize_host_policies

def synchronize(sleep=None):
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
		if sleep:
			gevent.sleep()

		syncer = ISyncableContentPackageLibrary(site_lib, None)
		if syncer is not None:
			logger.info("Sync library %s", site_lib)
			return site_lib.syncContentPackages()

	# sync
	results = run_job_in_all_host_sites(sync_site_library)
	gc.collect()
	
	# mark sync time
	hostsites = component.getUtility(IEtcNamespace, name='hostsites')
	hostsites.lastSynchronized = time.time()
	
	# notify
	notify(AllContentPackageLibrariesDidSyncEvent())
	
	# return results
	result = [ (x[0].__name__, x[1]) for x in results if x is not None]
	return result
