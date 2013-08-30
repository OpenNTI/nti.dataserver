#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from nti.externalization.externalization import toExternalObject

from nti.dataserver.tests import mock_dataserver
from nti.appserver.tests.test_application import SharedApplicationTestBase, WithSharedApplicationMockDS

from hamcrest import (assert_that, has_entry, has_item)

class TestPreferencesDecorators(SharedApplicationTestBase):

	@WithSharedApplicationMockDS
	def test_decorator(self):
		with mock_dataserver.mock_db_trans(self.ds):
			u = self._create_user()
			ext = toExternalObject(u)

		assert_that(ext, has_entry('Links', has_item(has_entry('rel', 'set_preferences'))))
		assert_that(ext, has_entry('Links', has_item(has_entry('rel', 'get_preferences'))))
		assert_that(ext, has_entry('Links', has_item(has_entry('rel', 'delete_preferences'))))
