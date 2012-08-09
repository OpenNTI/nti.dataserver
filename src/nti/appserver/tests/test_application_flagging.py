#!/usr/bin/env python
from __future__ import print_function

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904

from hamcrest import (assert_that, is_, none, starts_with,
					  has_entry, has_length, has_item, has_key,
					  contains_string, ends_with, all_of, has_entries)
from hamcrest import greater_than
from hamcrest import not_none
from hamcrest.library import has_property
from hamcrest import greater_than_or_equal_to


from webtest import TestApp

import os.path

import urllib

from nti.ntiids import ntiids
from nti.externalization.oids import to_external_ntiid_oid
from nti.dataserver import contenttypes
from nti.contentrange import contentrange

from nti.dataserver.tests import mock_dataserver

from .test_application import ApplicationTestBase

from urllib import quote as UQ

class TestApplicationGlossary(ApplicationTestBase):


	def test_flag_note(self):
		"We get the appropriate @@flag or @@flag.metoo links for a note"
		with mock_dataserver.mock_db_trans( self.ds ):
			user = self._create_user()

			n = contenttypes.Note()
			n.applicableRange = contentrange.ContentRangeDescription()
			n.containerId = 'tag:nti:foo'
			user.addContainedObject( n )

		testapp = TestApp( self.app )
		data = ''
		path = '/dataserver2/users/sjohnson@nextthought.com/Objects/%s' % to_external_ntiid_oid( n )
		path = UQ( path )
		# Initially, unflagged, I get asked to favorite
		res = testapp.get( path, extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 200 ) )
		assert_that( res.json_body, has_entry( 'Links', has_item( has_entry( 'rel', 'flag' ) ) ) )

		# So I do
		__traceback_info__ = res.json_body
		res = testapp.post( path + '/@@flag', data, extra_environ=self._make_extra_environ() )
		# and now I'm asked to re-flag
		assert_that( res.status_int, is_( 200 ) )
		assert_that( res.json_body, has_entry( 'Links', has_item( has_entry( 'rel', 'flag.metoo' ) ) ) )

		# And I can repeat
		res = testapp.post( path + '/@@flag.metoo', data, extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 200 ) )
		assert_that( res.json_body, has_entry( 'LikeCount', 0 ) )
		assert_that( res.json_body, has_entry( 'Links', has_item( has_entry( 'rel', 'like' ) ) ) )
		assert_that( res.json_body, has_entry( 'Links', has_item( has_entry( 'rel', 'favorite' ) ) ) )
		assert_that( res.json_body, has_entry( 'Links', has_item( has_entry( 'rel', 'flag.metoo' ) ) ) )


	def test_flag_moderation(self):
		"Basic tests of the moderation admin page"
		with mock_dataserver.mock_db_trans( self.ds ):
			user = self._create_user()
			n = contenttypes.Note()
			n.body = ['The first part']
			n.applicableRange = contentrange.ContentRangeDescription()
			n.containerId = 'tag:nti:foo'
			user.addContainedObject( n )

			n2 = contenttypes.Note()
			n2.body = ['The second part']
			n2.applicableRange = contentrange.ContentRangeDescription()
			n2.containerId = 'tag:nti:foo'
			user.addContainedObject( n2 )

		testapp = TestApp( self.app )

		# First, give us something to flag
		for i in (n, n2):
			path = '/dataserver2/users/sjohnson@nextthought.com/Objects/%s' % to_external_ntiid_oid( i )
			path = UQ( path )
			testapp.post( path + '/@@flag', '', extra_environ=self._make_extra_environ() )


		path = '/dataserver2/@@moderation_admin'

		res = testapp.get( path, extra_environ=self._make_extra_environ() )
		assert_that( res.status_int, is_( 200 ) )

		assert_that( res.content_type, is_( 'text/html' ) )
		assert_that( res.body, contains_string( 'The first part' ) )
		assert_that( res.body, contains_string( 'The second part' ) )

		# Initially ascending
		assert_that( res.body, contains_string( '?table-sortOrder=ascending&table-sortOn=table-note-created-1' ) )
		# So request that
		res = testapp.get( path + '?table-sortOrder=ascending&table-sortOn=table-note-created-1', extra_environ=self._make_extra_environ() )
		# and we get the reverse link
		assert_that( res.body, contains_string( '?table-sortOrder=descending&table-sortOn=table-note-created-1' ) )

		res = testapp.get( path + '?table-sortOrder=ascending&table-sortOn=table-note-modified-2', extra_environ=self._make_extra_environ() )
