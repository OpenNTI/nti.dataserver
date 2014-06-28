#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

import unittest
from hamcrest import assert_that
from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import same_instance
from hamcrest import has_length
from hamcrest import has_property
from hamcrest import has_entries
from hamcrest import greater_than
from hamcrest import empty as is_empty


from nti.testing import base
from nti.testing.matchers import validly_provides

from nti.externalization.tests import externalizes

import os

from zope import component



from ..interfaces import IContentPackageLibrary
from .. import filesystem
from .. import subscribers
from .. import interfaces

from . import ContentlibraryLayerTest

from zope.site.interfaces import NewLocalSite
from zope.site.folder import Folder
from zope.site.site import LocalSiteManager

from zope.lifecycleevent.interfaces import IObjectAddedEvent
from zope.lifecycleevent.interfaces import IObjectModifiedEvent
from zope.schema.interfaces import IFieldUpdatedEvent

from zope.component import eventtesting

from nti.zodb.minmax import NumericMaximum

class TestSubscribers(ContentlibraryLayerTest):

	def setUp(self):
		global_library = self.global_library = filesystem.GlobalFilesystemContentPackageLibrary( os.path.dirname(__file__) )
		global_library.syncContentPackages()

		component.getGlobalSiteManager().registerUtility( global_library,
														  provided=IContentPackageLibrary )

	def tearDown(self):
		component.getGlobalSiteManager().unregisterUtility( self.global_library,
															provided=IContentPackageLibrary )


	def test_install_site_library(self):

		site = Folder()
		site.__name__ = 'Site'
		sm = LocalSiteManager(site)

		site.setSiteManager(sm)

		site_lib = subscribers.install_site_content_library( sm, NewLocalSite(sm))

		assert_that( sm.getUtility(interfaces.IContentUnitAnnotationUtility),
					 is_not( component.getUtility(interfaces.IContentUnitAnnotationUtility)) )

		assert_that( sm.getUtility(interfaces.IContentPackageLibrary),
					 is_( same_instance(site_lib) ))

		# Because the site is based beneath the global site, the local library
		# has access to the parent site content
		embed_paths = site_lib.pathsToEmbeddedNTIID('tag:nextthought.com,2011-10:testing-NTICard-temp.nticard.1')
		assert_that( embed_paths, has_length( 1 ) )

		# This also had the side effect of registering the bundle library
		assert_that( sm.queryUtility(interfaces.IContentPackageBundleLibrary),
					 validly_provides(interfaces.IContentPackageBundleLibrary))

		# The library's context site is the one we installed
		bundle_library = sm.getUtility(interfaces.IContentPackageBundleLibrary)
		assert_that( component.getSiteManager(bundle_library),
					 is_( same_instance(sm) ))


		# If we unregister the site library, the bundle library goes away too
		sm.unregisterUtility( site_lib, provided=interfaces.IPersistentContentPackageLibrary )
		assert_that( sm.queryUtility(interfaces.IContentPackageBundleLibrary),
					 is_(none()) )

	def test_install_site_library_sync_bundle(self):
		# Use a real site we have that includes a bundle directory
		global_library = self.global_library
		site_factory = interfaces.ISiteLibraryFactory(global_library)

		site = Folder()
		site.__name__ = 'localsite'
		sm = LocalSiteManager(site)
		site.setSiteManager(sm)

		site_lib = site_factory.library_for_site_named( 'localsite' )
		eventtesting.clearEvents()

		site_lib = subscribers.install_site_content_library( sm, NewLocalSite(sm))

		evts = eventtesting.getEvents(interfaces.IContentPackageBundleLibraryModifiedOnSyncEvent)
		assert_that( evts, has_length(1) )

		bundle_lib = evts[0].object
		bundle_bucket = evts[0].bucket

		evts = eventtesting.getEvents(
			IObjectAddedEvent,
			filter=lambda e: interfaces.IContentPackageBundle.providedBy(getattr(e, 'object', None) ))

		assert_that( evts, has_length(1) )
		assert_that( evts[0], has_property('object',
										   has_property('ContentPackages', has_length(1))) )


		### XXX: This doesn't exactly belong here, it's just convenient

		# test externalization

		bundle = evts[0].object
		assert_that( bundle, validly_provides(interfaces.IContentPackageBundle) )

		# check that we have the right kind of property, didn't overwrite through createFieldProperties
		assert_that( bundle, has_property( '_lastModified', is_(NumericMaximum) ))

		assert_that( bundle, externalizes( has_entries('Class', 'ContentPackageBundle',
													   'ContentPackages', has_length(1),
													   'title', 'A Title',
													   'root', '/localsite/ContentPackageBundles/ABundle/',
													   'NTIID', bundle.ntiid,
													   'Last Modified', greater_than(0),
												   )))

		# test update existing object

		bundle.lastModified = 0
		eventtesting.clearEvents()
		interfaces.ISyncableContentPackageBundleLibrary(bundle_lib).syncFromBucket(bundle_bucket)

		evts = eventtesting.getEvents(IObjectModifiedEvent)

		assert_that( evts, has_length(2))
		assert_that( evts[0], has_property( 'object', is_(bundle) ))
		assert_that( evts[1], validly_provides(interfaces.IContentPackageBundleLibraryModifiedOnSyncEvent))

		# there are some field events, but none of them are for this object
		evts = eventtesting.getEvents(
			IFieldUpdatedEvent,
			filter=lambda e: not interfaces.IContentPackageBundle.providedBy(e.inst))
		assert_that( evts, is_empty() )
