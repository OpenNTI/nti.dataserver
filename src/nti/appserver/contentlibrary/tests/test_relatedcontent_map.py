#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import assert_that
from hamcrest import is_
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import has_property

from zope import component

from nti.contentlibrary import interfaces as lib_interfaces


from nti.appserver import interfaces as app_interfaces
from nti.appserver.contentlibrary import _related_content_map as rcm_module


from nti.app.testing.application_webtest import ApplicationLayerTest
from . import CourseTestContentApplicationTestLayer


class TestRelatedContentIndexMap(ApplicationLayerTest):
	layer = CourseTestContentApplicationTestLayer

	def setUp(self):
		self.rc_map = rcm_module.RelatedContentIndexMap()
		component.provideUtility(self.rc_map, app_interfaces.IRelatedContentIndexMap)

	def tearDown(self):
		component.getGlobalSiteManager().unregisterUtility(self.rc_map, app_interfaces.IRelatedContentIndexMap)

	def test_check_rc_map(self):
		library = component.getUtility(lib_interfaces.IContentPackageLibrary)
		content_package = library.contentPackages[0]
		rc_map = component.getUtility(app_interfaces.IRelatedContentIndexMap)

		# add
		rcm_module.add_related_content_items_from_new_content(content_package, None)
		assert_that(rc_map, has_length(2))
		assert_that(rc_map,
					has_entry('tag:nextthought.com,2011-10:NTI-RelatedWorkRef-CourseTestContent.relatedworkref.0',
							  has_length(10)))
		assert_that(rc_map,
					has_entry('tag:nextthought.com,2011-10:NTI-RelatedWork-CourseTestContent.relatedwork.source1',
							  has_length(9)))

		assert_that(rc_map, has_property('by_container', has_length(2)))

		assert_that(rc_map.by_container,
					has_entry('tag:nextthought.com,2011-10:NTI-HTML-CourseTestContent.lesson1',
							 is_([u'tag:nextthought.com,2011-10:NTI-RelatedWorkRef-CourseTestContent.relatedworkref.0'])))

		assert_that(rc_map.by_container,
					has_entry('tag:nextthought.com,2011-10:NTI-HTML-CourseTestContent.course_test_content',
							 is_([u'tag:nextthought.com,2011-10:NTI-RelatedWork-CourseTestContent.relatedwork.source1'])))


		# remove
		rcm_module.remove_related_content_items_from_old_content(content_package, None)
		assert_that(rc_map, has_length(0))
		assert_that(rc_map, has_property('by_container', has_length(0)))
