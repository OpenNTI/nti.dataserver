#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import os

from zope import component

from nti.contentlibrary import interfaces as lib_interfaces
from nti.contentlibrary.filesystem import DynamicFilesystemLibrary as FileLibrary

from nti.appserver import interfaces as app_interfaces
from nti.appserver.contentlibrary import _videoindex_map as vim_module

from nti.testing.base import SharedConfiguringTestBase

from hamcrest import (assert_that, is_, has_entry, has_length, has_property)

class TestVideoIndexMap(SharedConfiguringTestBase):

	def setUp(self):
		library = FileLibrary(os.path.join(os.path.dirname(__file__), 'library'))
		component.provideUtility(library, lib_interfaces.IFilesystemContentPackageLibrary)
		video_map = vim_module.VideoIndexMap()
		component.provideUtility(video_map, app_interfaces.IVideoIndexMap)

	def test_check_video_map(self):
		library = component.getUtility(lib_interfaces.IFilesystemContentPackageLibrary)
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

