#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import greater_than

from nti.app.testing.decorators import WithSharedApplicationMockDS
from nti.app.testing.application_webtest import ApplicationLayerTest

class TestViews(ApplicationLayerTest):

	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_unregister_missing_objects(self):
		path = '/dataserver2/@@unregister_missing_objects'
		res = self.testapp.post_json(path, status=200)
		assert_that(res.json_body, has_entry('Broken', has_length(0)))
		assert_that(res.json_body, has_entry('Missing', has_length(0)))
		assert_that(res.json_body, has_entry('TotalBroken', is_(0)))
		assert_that(res.json_body, has_entry('TotalMissing', is_(0)))
		assert_that(res.json_body, has_entry('Total', is_(greater_than(0))))
