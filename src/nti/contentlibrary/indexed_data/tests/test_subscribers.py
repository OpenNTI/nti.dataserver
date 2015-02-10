#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import contains
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_property

import os

from zope import lifecycleevent

from nti.contentlibrary.filesystem import EnumerateOnceFilesystemLibrary as FileLibrary

from nti.contentlibrary.indexed_data.interfaces import IVideoIndexedDataContainer
from nti.contentlibrary.indexed_data.interfaces import ITimelineIndexedDataContainer
from nti.contentlibrary.indexed_data.interfaces import ISlideDeckIndexedDataContainer
from nti.contentlibrary.indexed_data.interfaces import IRelatedContentIndexedDataContainer

from nti.contentlibrary.tests import ContentlibraryLayerTest

class TestSubscribers(ContentlibraryLayerTest):

	def setUp(self):
		library_dir = os.path.join( os.path.dirname(__file__), 'library' )
		self.library = FileLibrary(library_dir)

	def _do_test(self, iface,
				 unit_ntiid='tag:nextthought.com,2011-10:NTI-HTML-CourseTestContent.lesson1',
				 entry_ntiid=None):

		self.library.syncContentPackages()
		unit = self.library.pathToNTIID(unit_ntiid)[-1]

		container = iface(unit)

		assert_that( container, has_length(1) )
		assert_that( container.get_data_items(),
					 contains( has_entry('ntiid',
										 entry_ntiid) ) )

		lifecycleevent.removed(self.library[0])

		assert_that( container, has_length(0) )
		assert_that( container, has_property('lastModified', -1))

		lifecycleevent.added(self.library[0])
		lifecycleevent.modified(self.library[0])
		assert_that( container, has_length(1) )

	def test_related_work(self):
		self._do_test(IRelatedContentIndexedDataContainer,
					  entry_ntiid='tag:nextthought.com,2011-10:NTI-RelatedWorkRef-CourseTestContent.relatedworkref.0')

	def test_video(self):
		self._do_test(IVideoIndexedDataContainer,
					  entry_ntiid="tag:nextthought.com,2011-10:NTI-NTIVideo-CourseTestContent.ntivideo.video1")
		
	def test_timeline(self):
		self._do_test(ITimelineIndexedDataContainer,
					  entry_ntiid="tag:nextthought.com,2011-10:OU-JSON:Timeline-CourseTestContent.timeline.heading_west")
		
	def test_slidedeck(self):
		self._do_test(ISlideDeckIndexedDataContainer,
					  entry_ntiid="tag:nextthought.com,2011-10:OU-NTISlideDeck-CourseTestContent.nsd.pres:Nested_Conditionals")
