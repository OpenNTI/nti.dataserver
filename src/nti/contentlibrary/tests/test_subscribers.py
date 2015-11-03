#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import none
from hamcrest import is_not
from hamcrest import has_key
from hamcrest import contains
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_entries
from hamcrest import has_property
from hamcrest import greater_than
from hamcrest import same_instance
from hamcrest import empty as is_empty
from hamcrest import contains_inanyorder
does_not = is_not

from nti.externalization.tests import externalizes

import os

from zope import component

from zope.component import eventtesting
from zope.component.hooks import site as current_site

from zope.annotation.interfaces import IAnnotations

from zope.lifecycleevent.interfaces import IObjectAddedEvent
from zope.lifecycleevent.interfaces import IObjectRemovedEvent
from zope.lifecycleevent.interfaces import IObjectModifiedEvent

from zope.site.folder import Folder
from zope.site.site import LocalSiteManager
from zope.site.interfaces import NewLocalSite

from zope.schema.interfaces import IFieldUpdatedEvent

from nti.contentlibrary import filesystem
from nti.contentlibrary import interfaces
from nti.contentlibrary import subscribers
from nti.contentlibrary.bundle import ContentPackageBundle
from nti.contentlibrary.interfaces import IContentPackageLibrary

from nti.zodb.minmax import NumericMaximum

from nti.contentlibrary.tests import ContentlibraryLayerTest

from nti.testing.matchers import validly_provides

class TestSubscribers(ContentlibraryLayerTest):

	def setUp(self):
		global_library = self.global_library \
			= filesystem.GlobalFilesystemContentPackageLibrary( os.path.dirname(__file__) )
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

		# If we set annotations while we're in the global site...
		unit = embed_paths[0][0]
		assert_that( IAnnotations(unit), does_not(has_key('foo')) )
		IAnnotations(unit)['foo'] = 42
		
		IAnnotations(unit)
		assert_that( IAnnotations(unit), has_key('foo')) # check the dict contract

		# ...we can read them in the child site...
		with current_site(site):
			assert_that(component.getSiteManager(), is_(same_instance(sm)))
			ann = IAnnotations(unit)
			assert_that( ann.get('foo'), is_(42))
			assert_that( bool(ann), is_(True))

			# ...and if we overwrite in the child...
			ann['foo'] = -1
			ann = IAnnotations(unit)
			assert_that( ann.get('foo'), is_(-1) )
			assert_that( ann, has_entry( 'foo', -1)) # check the dict contract

		# ... that doesn't make it to the parent
		assert_that(component.getSiteManager(), is_not(same_instance(sm)))
		ann = IAnnotations(unit)
		assert_that( ann.get('foo'), is_(42))
		assert_that( ann, has_entry( 'foo', 42)) # check the dict contract

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

		site_factory.library_for_site_named( 'localsite' )
		eventtesting.clearEvents()

		subscribers.install_site_content_library( sm, NewLocalSite(sm))

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

		bundle = evts[0].object
		assert_that( list(bundle_lib.getBundles()), contains(bundle) )
		assert_that( bundle_lib.get(bundle.ntiid), is_(bundle) )
		assert_that( bundle_lib.get('missing', 1), is_(1) )

		# XXX: This doesn't exactly belong here, it's just convenient

		# test externalization

		assert_that( bundle, validly_provides(interfaces.IContentPackageBundle) )

		# check that we have the right kind of property, didn't overwrite through createFieldProperties
		assert_that( bundle, has_property( '_lastModified', is_(NumericMaximum) ))

		assert_that( bundle, externalizes( has_entries('Class', 'ContentPackageBundle',
													   'ContentPackages', has_length(1),
													   'title', 'A Title',
													   'root', '/sites/localsite/ContentPackageBundles/ABundle/',
													   'NTIID', bundle.ntiid,
													   'Last Modified', greater_than(0),
													   'PlatformPresentationResources', contains_inanyorder(
														   has_entry('PlatformName', 'iPad'),
														   has_entry('PlatformName', 'webapp'),
														   has_entry('PlatformName', 'shared')),
													   'PlatformPresentationResources', contains_inanyorder(
														   has_entry('href', '/TestFilesystem/presentation-assets/iPad/v1/'),
														   has_entry('href', '/TestFilesystem/presentation-assets/webapp/v1/'),
														   has_entry('href', '/TestFilesystem/presentation-assets/shared/v1/')) )
									   ))

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
			filter=lambda e: interfaces.IContentPackageBundle.providedBy(e.inst))

		assert_that( evts, is_empty() )

		# we can do it again, and nothing changes
		eventtesting.clearEvents()
		interfaces.ISyncableContentPackageBundleLibrary(bundle_lib).syncFromBucket(bundle_bucket)

		evts = eventtesting.getEvents(IObjectModifiedEvent)
		assert_that( evts, has_length(0))

		# If we put a 'fake' bundle in there, if we sync again, it gets
		# removed
		fake_bundle = ContentPackageBundle()
		bundle_lib['tag:nextthought.com,2011-10:FOO-BAR-BAZ'] = fake_bundle

		eventtesting.clearEvents()
		interfaces.ISyncableContentPackageBundleLibrary(bundle_lib).syncFromBucket(bundle_bucket)

		evts = eventtesting.getEvents(IObjectRemovedEvent)
		assert_that( evts, has_length(1))

		assert_that( evts[0], has_property('object', is_(fake_bundle)))
