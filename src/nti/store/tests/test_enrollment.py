#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import assert_that

import unittest

from nti.dataserver.users import User

from nti.store import enrollment

from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.store.tests import SharedConfiguringTestLayer

from nose.tools import assert_raises

class TestEnrollment(unittest.TestCase):

	layer = SharedConfiguringTestLayer

	course_id = 'tag:nextthought.com,2011-10:OU-course-CLC3403LawAndJustice'

	def _create_user(self, username='nt@nti.com', password='temp001'):
		usr = User.create_user(self.ds, username=username, password=password)
		return usr

	@WithMockDSTrans
	def test_enrollment(self):
		user = self._create_user()
		assert_that(enrollment.is_enrolled(user, self.course_id), is_(False))

		r = enrollment.enroll_course(user, self.course_id)
		assert_that(r, is_(True))
		assert_that(enrollment.is_enrolled(user, self.course_id), is_(True))

		r = enrollment.enroll_course(user, self.course_id)
		assert_that(r, is_(False))

		r = enrollment.unenroll_course(user, self.course_id)
		assert_that(r, is_(True))
		assert_that(enrollment.is_enrolled(user, self.course_id), is_(False))

		with assert_raises(enrollment.UserNotEnrolledException):
			enrollment.unenroll_course(user, self.course_id)

		with assert_raises(enrollment.CourseNotFoundException):
			enrollment.unenroll_course(user, 'xxx')
