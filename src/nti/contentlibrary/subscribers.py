#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Event listeners.

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from .interfaces import IContentPackageLibrary
from .interfaces import ISiteLibraryFactory
from .interfaces import IPersistentContentPackageLibrary
from .interfaces import IContentUnitAnnotationUtility

from .annotation import ContentUnitAnnotationUtility

from zope.component.hooks import site

_LIBRARY_NAME = '++etc++library'

def install_site_content_library(local_site_manager, _=None):
	"""
	When a new local site, representing a site (host) policy
	is added, install a site-local library and associated utilities
	into it. The library is sync'd after this is done.

	If you need to perform work, such as registering your own
	utility in the local site that uses the local library, listen for the component
	registration event, :class:`zope.interface.interfaces.IRegistered`,
	which is an ObjectEvent, whose object will be an
	:class:`nti.contentlibrary.interfaces.IPersistentContentPackageLibrary`.

	Although this function is ordinarily called as an event listener
	for a :class:`.INewLocalSite` event, it can also be called
	manually, passing in just a site manager. In that case, if there
	is no local library, and one can now be found, it will be created;
	if a local library already exists, nothing will be done.

	:returns: The site local content library, if one was found or installed.
	"""

	if _ is None and _LIBRARY_NAME in local_site_manager:
		lib = local_site_manager[_LIBRARY_NAME]
		logger.debug("Nothing to do for site %s, library already present %s",
					 local_site_manager, lib)
		return lib

	global_library = component.getGlobalSiteManager().queryUtility(IContentPackageLibrary)
	if global_library is None:
		logger.warning("New site installed without global library; will not have local library")
		return

	local_site = local_site_manager.__parent__
	assert bool(local_site.__name__), "sites must be named"


	site_library_factory = ISiteLibraryFactory(global_library, None)
	if site_library_factory is None:
		logger.warning( "No site factory for %s; should only happen in tests", global_library)
		return

	library = site_library_factory.library_for_site_named( local_site.__name__ )
	logger.info("Installing site library %s for %s",
				library, local_site.__name__)
	assert IPersistentContentPackageLibrary.providedBy(library)

	# Contain the utilities we are about to install.
	# Note that for queryNextUtility, etc, to work properly if they
	# use themselves as the context (which seems to be what people do)
	# these need to be children of the SiteManager object: qNU walks from
	# the context to the enclosing site manager, and then looks through ITS
	# bases
	local_site_manager[_LIBRARY_NAME] = library
	local_site_manager['++etc++contentannotation'] = annotes = ContentUnitAnnotationUtility()


	# Before we install (which fires a registration event that things might
	# be listening for) set up the dependent utilities
	local_site_manager.registerUtility( annotes,
										provided=IContentUnitAnnotationUtility)

	# Now we can register and sync our site library
	local_site_manager.registerUtility( library,
										provided=IPersistentContentPackageLibrary )

	with site(local_site):
		# sync in this site so the right utilities and event
		# listeners are found
		library.syncContentPackages()
		return library

### Bundle-related subscribers

from zope.interface.interfaces import IRegistered
from zope.interface.interfaces import IUnregistered

from .interfaces import IContentPackageBundleLibrary
from .interfaces import IContentPackageLibraryDidSyncEvent
from .interfaces import IDelimitedHierarchyContentPackageEnumeration
from .interfaces import ISyncableContentPackageBundleLibrary

from .bundle import ContentPackageBundleLibrary

_BUNDLE_LIBRARY_NAME = 'ContentPackageBundles' # because it might be in traversal paths

@component.adapter(IPersistentContentPackageLibrary, IRegistered)
def install_bundle_library(library, event):
	"""
	When a new persistent library is installed, beside it we
	put something to manage (persistent) content bundles, driven
	off the bucket that the library manages.
	"""
	registration = event.object
	local_site_manager = registration.registry

	# See above for why these need to be in the site manager
	bundle_library = local_site_manager[_BUNDLE_LIBRARY_NAME] = ContentPackageBundleLibrary()

	local_site_manager.registerUtility( bundle_library,
										provided=IContentPackageBundleLibrary )


@component.adapter(IPersistentContentPackageLibrary, IUnregistered)
def uninstall_bundle_library(library, event):
	registration = event.object
	local_site_manager = registration.registry

	bundle_library = local_site_manager[_BUNDLE_LIBRARY_NAME]

	local_site_manager.unregisterUtility( bundle_library,
										  provided=IContentPackageBundleLibrary )
	del local_site_manager[_BUNDLE_LIBRARY_NAME]

@component.adapter(IPersistentContentPackageLibrary, IContentPackageLibraryDidSyncEvent)
def sync_bundles_when_library_synched(library, event):
	"""
	When a persistent content library is synchronized
	with the disk contents, whether or not anything actually changed,
	we also synchronize the corresponding bundle library. (Because they could
	change independently and in unknown ways)
	"""

	# Find the local site manager
	site_manager = component.getSiteManager(library)
	if library.__parent__ is not site_manager:
		logger.warn("Expected to find persistent library in its own site; refusing to sync")
		return

	bundle_library = site_manager.getUtility(IContentPackageBundleLibrary)
	assert bundle_library.__parent__ is site_manager, "Make sure we got the immediate parent"

	enumeration = IDelimitedHierarchyContentPackageEnumeration(library)

	enumeration_root = enumeration.root

	bundle_bucket = enumeration_root.getChildNamed(bundle_library.__name__)
	if bundle_bucket is None:
		logger.info("No child named %s in %s for library %s",
					bundle_library.__name__, getattr(enumeration_root, 'absolute_path', enumeration_root),
					library)
		return

	ISyncableContentPackageBundleLibrary(bundle_library).syncFromBucket(bundle_bucket)
