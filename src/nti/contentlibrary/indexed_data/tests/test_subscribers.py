# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import os
import fudge

from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import contains_inanyorder

from zope import component

from zope.component.persistentregistry import PersistentComponents as Components

from persistent import Persistent

from nti.contentlibrary.filesystem import EnumerateOnceFilesystemLibrary as FileLibrary

from nti.contentlibrary.interfaces import IContentPackageLibrary

from nti.contentlibrary.indexed_data import get_catalog
from nti.app.contentlibrary.subscribers import _clear_when_removed

from nti.contenttypes.presentation.interfaces import INTIVideo
from nti.contenttypes.presentation.interfaces import INTITimeline
from nti.contenttypes.presentation.interfaces import INTISlideDeck
from nti.contenttypes.presentation.interfaces import INTIRelatedWorkRef

from nti.contentlibrary.tests import ContentlibraryLayerTest

import nti.dataserver.tests.mock_dataserver as mock_dataserver
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

class PersistentComponents(Components, Persistent):
	pass

class TestSubscribers(ContentlibraryLayerTest):

	def setUp(self):
		super(ContentlibraryLayerTest, self).setUp()
		self.library_dir = os.path.join(os.path.dirname(__file__), 'library')
		self.library = FileLibrary(self.library_dir)
		component.getGlobalSiteManager().registerUtility(self.library, IContentPackageLibrary)

	def tearDown(self):
		component.getGlobalSiteManager().unregisterUtility(self.library, IContentPackageLibrary)

	@WithMockDSTrans
	@fudge.patch('nti.app.contentlibrary.subscribers._registry')
	def test_indexing(self, mock_registry):
		registry = PersistentComponents()
		mock_dataserver.current_transaction.add(registry)
		mock_registry.is_callable().returns(registry)

		unit_ntiid = 'tag:nextthought.com,2011-10:NTI-HTML-CourseTestContent.lesson1'
		self.library.syncContentPackages()
		content_package = self.library.contentPackages[0]
		catalog = get_catalog()
		results = catalog.search_objects(container_ntiids=(unit_ntiid,))
		assert_that(results, has_length(4))

		# Namespace
		results = catalog.search_objects(namespace=content_package.ntiid)
		assert_that(results, has_length(5))

		# Type
		for provided, count in (('INTIVideo', 1),
								('INTIRelatedWorkRef', 2),
								('INTISlideDeck', 1),
								('INTITimeline', 1)):
			results = catalog.search_objects(provided=provided)
			assert_that(results, has_length(count))

		results = catalog.search_objects(provided='audio')
		assert_that(results, has_length(0))

		# Containers
		item_ntiid = 'tag:nextthought.com,2011-10:NTI-RelatedWorkRef-CourseTestContent.relatedworkref.0'
		obj = registry.queryUtility(INTIRelatedWorkRef, name=item_ntiid)
		containers = catalog.get_containers(obj)
		exp_containers = self.library.pathToNTIID(unit_ntiid)
		exp_containers = [x.ntiid for x in exp_containers]
		assert_that(containers, contains_inanyorder(*exp_containers))

		item_ntiid = "tag:nextthought.com,2011-10:NTI-NTIVideo-CourseTestContent.ntivideo.video1"
		obj = registry.queryUtility(INTIVideo, name=item_ntiid)
		containers = catalog.get_containers(obj)
		assert_that(containers, contains_inanyorder(*exp_containers))

		item_ntiid = "tag:nextthought.com,2011-10:OU-JSON:Timeline-CourseTestContent.timeline.heading_west"
		obj = registry.queryUtility(INTITimeline, name=item_ntiid)
		containers = catalog.get_containers(obj)
		assert_that(containers, contains_inanyorder(*exp_containers))

		item_ntiid = "tag:nextthought.com,2011-10:OU-NTISlideDeck-CourseTestContent.nsd.pres:Nested_Conditionals"
		obj = registry.queryUtility(INTISlideDeck, name=item_ntiid)
		containers = catalog.get_containers(obj)
		assert_that(containers, contains_inanyorder(*exp_containers))

		# DNE
		item_ntiid = "tag:nextthought.com,2011-10:OU-NTISlideDeck-CourseTestContent.nsd.pres:Nested_Conditionalsxxxx"
		obj = registry.queryUtility(INTISlideDeck, name=item_ntiid)
		containers = catalog.get_containers(obj)
		assert_that(containers, has_length(0))

		# Clear everything
		_clear_when_removed(content_package)

		for provided in ('video', 'relatedwork', 'slidedeck', 'timeline', 'audio'):
			results = catalog.search_objects(provided=provided)
			assert_that(results, has_length(0))

		item_ntiid = 'tag:nextthought.com,2011-10:NTI-RelatedWorkRef-CourseTestContent.relatedworkref.0'
		obj = registry.queryUtility(INTIRelatedWorkRef, name=item_ntiid)
		containers = catalog.get_containers(obj)
		assert_that(containers, has_length(0))

		results = catalog.search_objects(container_ntiids=(unit_ntiid,))
		assert_that(results, has_length(0))

		# Re-index does nothing (since files have not changed)
		# Touch our content package, but not the index files
		self.library.syncContentPackages()
		results = catalog.search_objects(container_ntiids=(unit_ntiid,))
		assert_that(results, has_length(0))
