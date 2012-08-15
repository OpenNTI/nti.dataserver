#!/usr/bin/env python
from __future__ import print_function

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

from hamcrest import assert_that
from hamcrest import has_entry
from hamcrest import is_
from hamcrest import has_item
from hamcrest import all_of
from hamcrest import contains_string
from hamcrest import has_property


from webtest import TestApp

from nti.dataserver.tests import mock_dataserver

from .test_application import ApplicationTestBase



class TestApplicationUserSearch(ApplicationTestBase):

	def test_user_search(self):
		with mock_dataserver.mock_db_trans(self.ds):
			_ = self._create_user()

		testapp = TestApp( self.app )
		res = testapp.get( '/dataserver2', extra_environ=self._make_extra_environ())
		# The service do contains a link
		assert_that( res.json_body['Items'], has_item( all_of(
															has_entry( 'Title', 'Global' ),
															has_entry( 'Links', has_item( has_entry( 'href', '/dataserver2/UserSearch' ) ) ) ) ) )

		# We can search for ourself
		path = '/dataserver2/UserSearch/sjohnson@nextthought.com'
		res = testapp.get( path, extra_environ=self._make_extra_environ())

		assert_that( res.content_type, is_( 'application/vnd.nextthought+json' ) )
		assert_that( res.cache_control, has_property( 'no_store', True ) )

		assert_that( res.body, contains_string( str('sjohnson@nextthought.com') ) )

		# We should have an edit link when we find ourself
		assert_that( res.json_body['Items'][0], has_entry( 'Links',
												  has_item( all_of(
													  has_entry( 'href', "/dataserver2/users/sjohnson%40nextthought.com" ),
													  has_entry( 'rel', 'edit' ) ) ) ) )


	def test_search_empty_term_user(self):
		"Searching with an empty term returns empty results"
		with mock_dataserver.mock_db_trans( self.ds ):
			_ = self._create_user()

		testapp = TestApp( self.app )
		# The results are not defined across the search types,
		# we just test that it doesn't raise a 404
		for search_path in ('UserSearch',):
			for ds_path in ('dataserver2',):
				path = '/' + ds_path +'/' + search_path + '/'
				res = testapp.get( path, extra_environ=self._make_extra_environ())
				assert_that( res.status_int, is_( 200 ) )
