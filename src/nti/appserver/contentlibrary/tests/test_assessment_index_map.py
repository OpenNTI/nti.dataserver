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
from nti.appserver.contentlibrary import _question_map as qm_module

from nti.app.testing.base import SharedConfiguringTestBase

from hamcrest import (assert_that, has_length, has_property)

class TestAssessmentIndexMap(SharedConfiguringTestBase):

	def setUp(self):
		library = FileLibrary(os.path.join(os.path.dirname(__file__), 'library'))
		component.provideUtility(library, lib_interfaces.IFilesystemContentPackageLibrary)
		question_map = qm_module.QuestionMap()
		component.provideUtility(question_map, app_interfaces.IFileQuestionMap)

	def test_check_question_map(self):
		library = component.getUtility(lib_interfaces.IFilesystemContentPackageLibrary)
		content_package = library.contentPackages[0]
		q_map = component.getUtility(app_interfaces.IFileQuestionMap)
		qm_module.add_assessment_items_from_new_content(content_package, None)
		# remove
		qm_module.remove_assessment_items_from_oldcontent(content_package, None)
		assert_that(q_map, has_length(0))
		assert_that(q_map, has_property('by_file', has_length(0)))
