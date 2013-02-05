#!/usr/bin/env python
from __future__ import print_function

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

from hamcrest import (assert_that, is_, none, starts_with,
					  has_entry, has_length, has_item, has_key,
					  contains_string, ends_with, all_of, has_entries)

from .test_application import TestApp

from nti.dataserver.tests import mock_dataserver

from .test_application import SharedApplicationTestBase, WithSharedApplicationMockDS


###
# Note: These are more integration tests than unit tests,
# and require an internet connection.
##
class TestApplicationLiveImageUrl(SharedApplicationTestBase):


	@WithSharedApplicationMockDS
	def test_echo_bad_param(self):
		with mock_dataserver.mock_db_trans( self.ds ):
			user = self._create_user()

		testapp = TestApp( self.app )

		path = '/dataserver2/@@echo_image_url?image_url=foo'
		environ = self._make_extra_environ()
		res = testapp.get( path,
						   extra_environ=environ,
						   status=400)


	@WithSharedApplicationMockDS
	def test_echo_correct_image(self):
		with mock_dataserver.mock_db_trans( self.ds ):
			user = self._create_user()

		testapp = TestApp( self.app )

		path = '/dataserver2/@@echo_image_url?image_url=http://www.python.org/images/python-logo.gif'
		environ = self._make_extra_environ()
		res = testapp.get( path,
						   extra_environ=environ,
						   status=200)

		assert_that( res.content_type, is_( 'image/gif' ) )



	@WithSharedApplicationMockDS
	def test_echo_404(self):
		with mock_dataserver.mock_db_trans( self.ds ):
			user = self._create_user()

		testapp = TestApp( self.app )

		path = '/dataserver2/@@echo_image_url?image_url=http://www.python.org/images/python-logo.gif.missing'
		environ = self._make_extra_environ()
		testapp.get( path,
					 extra_environ=environ,
					 status=404)

	@WithSharedApplicationMockDS
	def test_echo_wrong_target_type(self):
		with mock_dataserver.mock_db_trans( self.ds ):
			user = self._create_user()

		testapp = TestApp( self.app )

		path = '/dataserver2/@@echo_image_url?image_url=http://www.python.org/index.html'
		environ = self._make_extra_environ()
		testapp.get( path,
					 extra_environ=environ,
					 status=404)
