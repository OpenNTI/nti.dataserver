#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import os

from hamcrest import assert_that
from hamcrest import is_
from hamcrest import none
from hamcrest import same_instance

from zope import component

from nti.assessment import interfaces as asm_interfaces

from nti.contentlibrary import interfaces as lib_interfaces
# NOTE: This does not work with a totally DynamicFilesystemLibrary,
# as new packages are generated and annotations are lost!
from nti.contentlibrary.filesystem import EnumerateOnceFilesystemLibrary as FileLibrary

from nti.appserver import interfaces as app_interfaces
from nti.appserver.contentlibrary import _question_map as qm_module

from nti.app.testing.base import SharedConfiguringTestBase

class TestAssessmentIndexMap(SharedConfiguringTestBase):

	def setUp(self):
		library = FileLibrary(os.path.join(os.path.dirname(__file__), 'library'))
		component.provideUtility(library, lib_interfaces.IFilesystemContentPackageLibrary)
		question_map = qm_module.QuestionMap()
		component.provideUtility(question_map, app_interfaces.IFileQuestionMap)

	def test_check_question_map(self):
		library = component.getUtility(lib_interfaces.IFilesystemContentPackageLibrary)
		content_package = library.contentPackages[0]
		component.getUtility(app_interfaces.IFileQuestionMap)
		#qm_module.add_assessment_items_from_new_content(content_package, None)

		# The question and sets are registered, and are the same instance
		question_set = component.getUtility( asm_interfaces.IQuestionSet,
											 name="tag:nextthought.com,2011-10:NTI-NAQ-CourseTestContent.naq.set.qset:QUIZ1_aristotle" )
		for question in question_set.questions:
			assert_that( question, is_( same_instance( component.getUtility( asm_interfaces.IQuestion,
																			 name=question.ntiid ))))
		# remove
		qm_module.remove_assessment_items_from_oldcontent(content_package, None)

		# And everything is gone.
		assert_that( component.queryUtility( asm_interfaces.IQuestionSet, question_set.ntiid ),
					 is_( none() ) )
