#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_not
from hamcrest import has_length
from hamcrest import assert_that
does_not = is_not

import os

from nti.contentrendering.contentchecks.courseinfo import validator

from nti.contentrendering.contentchecks.courseinfo.tests import CourseinfoLayerTest

class TestValidator(CourseinfoLayerTest):

	def test_validate(self):
		course_info = os.path.join(os.path.dirname(__file__), "course_info.json")
		result = validator.validate_file(course_info)
		assert_that(result, has_length(4))