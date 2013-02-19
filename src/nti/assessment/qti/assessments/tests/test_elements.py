#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

import os

from .. import elements

from ... import find_concrete_classes
from ... import find_concrete_interfaces

from ...tests import ConfiguringTestBase

from hamcrest import (assert_that, has_property, has_length)
		
class TestAssesmentsElements(ConfiguringTestBase):
	
	def test_assessmentTest(self):
	
		assert_that(elements.AssessmentTest, has_property('_v_definitions'))
		assert_that(elements.AssessmentTest, has_property('_v_attributes'))
		
		f = elements.AssessmentTest()
		assert_that(f, has_property('outcomeDeclaration'))
		assert_that(f, has_property('timeLimits'))
		assert_that(f, has_property('testPart'))
		assert_that(f, has_property('outcomeProcessing'))
		assert_that(f, has_property('testFeedback'))

	def test_consistency(self):
		path = os.path.dirname(elements.__file__)
		classes = find_concrete_classes(path)
		interfaces = find_concrete_interfaces(path)
		assert_that(classes, has_length(len(interfaces)))
