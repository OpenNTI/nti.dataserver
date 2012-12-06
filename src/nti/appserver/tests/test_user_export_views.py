#!/usr/bin/env python
from __future__ import print_function

import unittest

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import assert_that
from hamcrest import has_entry
from hamcrest import has_item

from hamcrest import contains
from hamcrest import has_entries

from hamcrest import is_not as does_not
from hamcrest import ends_with

import anyjson as json
from webtest import TestApp

import urllib

from nti.dataserver.tests import mock_dataserver
from nti.dataserver import users
from nti.appserver.tests.test_application import SharedApplicationTestBase, WithSharedApplicationMockDS

class TestApplicationUserExporViews(SharedApplicationTestBase):

	@WithSharedApplicationMockDS
	def test_user_info_extract(self):
		with mock_dataserver.mock_db_trans( self.ds ):
			owner = self._create_user()

		testapp = TestApp( self.app )

		path = '/dataserver2/@@user_info_extract'
		environ = self._make_extra_environ()
		environ[b'HTTP_ORIGIN'] = b'http://mathcounts.nextthought.com'
		
		res = testapp.get( path, extra_environ=environ )
		assert_that( res.status_int, is_( 200 ) )

if __name__ == '__main__':
	unittest.main()
	