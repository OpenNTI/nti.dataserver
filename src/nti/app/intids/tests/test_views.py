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

import zope.intid

from zope import component

from nti.dataserver.tests import mock_dataserver

from nti.app.testing.decorators import WithSharedApplicationMockDS
from nti.app.testing.application_webtest import ApplicationLayerTest

class TestViews(ApplicationLayerTest):

	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_unregister_missing_objects(self):
		path = '/dataserver2/@@UnregisterMissingObjects'
		res = self.testapp.post_json(path, status=200)
		assert_that(res.json_body, has_entry('Broken', has_length(0)))
		assert_that(res.json_body, has_entry('Missing', has_length(0)))
		assert_that(res.json_body, has_entry('TotalBroken', is_(0)))
		assert_that(res.json_body, has_entry('TotalMissing', is_(0)))
		assert_that(res.json_body, has_entry('Total', is_(greater_than(0))))

	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_intid_resolver(self):
		with mock_dataserver.mock_db_trans(self.ds):
			user = self._get_user()
			intids = component.getUtility(zope.intid.IIntIds)
			uid = intids.getId(user)
		path = '/dataserver2/@@IntIdResolver/%s' % uid
		res = self.testapp.get(path, status=200)
		assert_that(res.json_body, has_entry('Class', 'User'))
