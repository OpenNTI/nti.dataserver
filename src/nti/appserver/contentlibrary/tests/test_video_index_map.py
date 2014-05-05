#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_property

from zope import component

from nti.contentlibrary import interfaces as lib_interfaces

from nti.appserver.contentlibrary import interfaces as app_interfaces
from nti.appserver.contentlibrary import _video_index_map as vim_module

from nti.app.testing.application_webtest import ApplicationLayerTest

from . import CourseTestContentApplicationTestLayer

class TestVideoIndexMap(ApplicationLayerTest):

	layer = CourseTestContentApplicationTestLayer

	def setUp(self):
		self.video_map = vim_module.VideoIndexMap()
		component.provideUtility(self.video_map, app_interfaces.IVideoIndexMap)

	def tearDown(self):
		component.getGlobalSiteManager().unregisterUtility(self.video_map, app_interfaces.IVideoIndexMap)

	def test_check_video_map(self):
		library = component.getUtility(lib_interfaces.IContentPackageLibrary)
		content_package = library.contentPackages[0]
		vi_map = component.getUtility(app_interfaces.IVideoIndexMap)

		# add
		vim_module.add_video_items_from_new_content(content_package, None)
		assert_that(vi_map, has_property('by_container', has_length(1)))
		assert_that(vi_map.by_container,
					has_entry('tag:nextthought.com,2011-10:NTI-HTML-CourseTestContent.lesson1',
							 is_([u'tag:nextthought.com,2011-10:NTI-NTIVideo-CourseTestContent.ntivideo.video1'])))

		# remove
		vim_module.remove_video_items_from_old_content(content_package, None)
		assert_that(vi_map, has_property('by_container', has_length(0)))
