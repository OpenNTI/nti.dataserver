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
from .interfaces import IPersistentContentPackageLibary
from .interfaces import IContentUnitAnnotationUtility

from .annotation import ContentUnitAnnotationUtility

from zope.component.hooks import site

# Note we don't declare what we adapt here, we keep
# that in the zcml...the location of the interface
# for local_site should be moving
def install_site_content_library(local_site_manager, event):
	"""
	When a new local site, representing a site (host) policy
	is added, install a site-local library and associated utilities
	into it. The library is sync'd after this is done.

	If you need to perform work, such as registering your own
	utility in the local site, listen for the component
	registration event, :class:`zope.interface.interfaces.IRegistered`,
	which is an ObjectEvent, whose object will be an
	:class:`nti.contentlibrary.interfaces.IPersistentContentPackageLibary`
	"""

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
	assert IPersistentContentPackageLibary.providedBy(library)

	# Contain the utilities we are about to install.
	# Note that for queryNextUtility, etc, to work properly if they
	# use themselves as the context (which seems to be what people do)
	# these need to be children of the SiteManager object: qNU walks from
	# the context to the enclosing site manager, and then looks through ITS
	# bases
	local_site_manager['++etc++library'] = library
	local_site_manager['++etc++contentannotation'] = annotes = ContentUnitAnnotationUtility()


	# Before we install (which fires a registration event that things might
	# be listening for) set up the dependent utilities
	local_site_manager.registerUtility( annotes,
										provided=IContentUnitAnnotationUtility)

	# Now we can register and sync our site library
	local_site_manager.registerUtility( library,
										provided=IPersistentContentPackageLibary )

	with site(local_site):
		# sync in this site so the right utilities and event
		# listeners are found
		library.syncContentPackages()
		return library

from zope.interface.interfaces import IRegistered
from zope.interface.interfaces import IUnregistered

from .interfaces import IContentPackageBundleLibrary
from .bundle import ContentPackageBundleLibrary

_BUNDLE_LIBRARY_NAME = 'ContentPackageBundles'

@component.adapter(IPersistentContentPackageLibary, IRegistered)
def install_bundle_library(library, event):
	registration = event.object
	local_site_manager = registration.registry

	# See above for why these need to be in the site manager
	bundle_library = local_site_manager[_BUNDLE_LIBRARY_NAME] = ContentPackageBundleLibrary()

	local_site_manager.registerUtility( bundle_library,
										provided=IContentPackageBundleLibrary )


@component.adapter(IPersistentContentPackageLibary, IUnregistered)
def uninstall_bundle_library(library, event):
	registration = event.object
	local_site_manager = registration.registry

	bundle_library = local_site_manager[_BUNDLE_LIBRARY_NAME]

	local_site_manager.unregisterUtility( bundle_library,
										  provided=IContentPackageBundleLibrary )
	del local_site_manager[_BUNDLE_LIBRARY_NAME]
