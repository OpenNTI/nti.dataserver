#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

from ..elements import AssessmentTest

from nti.assessment.qti.tests import ConfiguringTestBase

from hamcrest import (assert_that, has_property)
		
class TestAssesmentsElement(ConfiguringTestBase):
	
	def test_assessmentTest(self):
	
		assert_that(AssessmentTest, has_property('_v_definitions'))
		assert_that(AssessmentTest, has_property('_v_attributes'))
		
		f = AssessmentTest()
		assert_that(f, has_property('outcomeDeclaration'))
		assert_that(f, has_property('timeLimits'))
		assert_that(f, has_property('testPart'))
		assert_that(f, has_property('outcomeProcessing'))
		assert_that(f, has_property('testFeedback'))
