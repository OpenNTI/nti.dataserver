#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import simplejson

from nti.dataserver.tests import mock_dataserver
from nti.appserver.tests.test_application import SharedApplicationTestBase, WithSharedApplicationMockDS

from nti.appserver.tests.test_application import TestApp

from hamcrest import (assert_that, has_entry, has_item, has_length, is_)

class TestPreferencesDecorators(SharedApplicationTestBase):

	@WithSharedApplicationMockDS
	def test_decorator(self):
		with mock_dataserver.mock_db_trans(self.ds):
			u = self._create_user()
			username = u.username

		testapp = TestApp(self.app)

		path = '/dataserver2/ResolveUser/%s' % username
		environ = self._make_extra_environ()
		res = testapp.get(path, extra_environ=environ)
		assert_that(res.status_int, is_(200))
		d = simplejson.loads(res.body)
		assert_that(d, has_entry(u'Items', has_length(1)))
		ext = d['Items'][0]
		assert_that(ext, has_entry('Links', has_item(has_entry('rel', 'set_preferences'))))
		assert_that(ext, has_entry('Links', has_item(has_entry('rel', 'get_preferences'))))
		assert_that(ext, has_entry('Links', has_item(has_entry('rel', 'delete_preferences'))))
