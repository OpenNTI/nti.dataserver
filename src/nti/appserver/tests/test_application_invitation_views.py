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
from hamcrest import contains_string
from hamcrest import contains


import anyjson as json
from webtest import TestApp


from nti.dataserver.tests import mock_dataserver

from .test_application import SharedApplicationTestBase, WithSharedApplicationMockDS


class TestApplicationInvitationViews(SharedApplicationTestBase):

	@WithSharedApplicationMockDS
	def test_link_in_user(self):
		with mock_dataserver.mock_db_trans( self.ds ):
			_ = self._create_user()

		testapp = TestApp( self.app )

		res = testapp.get( '/dataserver2/ResolveUser/sjohnson@nextthought.com',
							extra_environ=self._make_extra_environ() )

		assert_that( res.json_body['Items'][0], has_entry( 'Links', has_item( has_entries( 'rel', 'accept-invitations',
																						   'href', '/dataserver2/users/sjohnson%40nextthought.com/@@accept-invitations' ) ) ) )


	@WithSharedApplicationMockDS
	def test_invalid_invitation_code(self):
		with mock_dataserver.mock_db_trans( self.ds ):
			_ = self._create_user()

		testapp = TestApp( self.app )

		res = testapp.post( '/dataserver2/users/sjohnson@nextthought.com/@@accept-invitations',
							json.dumps( {'invitation_codes': ['foobar']} ),
							extra_environ=self._make_extra_environ(),
							status=422 )

		assert_that( res.json_body, has_entry( 'field', 'invitation_codes' ) )
		assert_that( res.json_body, has_entry( 'code', 'InvitationCodeError' ) )
		assert_that( res.json_body, has_entry( 'value', 'foobar' ) )
		assert_that( res.json_body, has_entry( 'message', contains_string( 'The invitation code is not valid.' ) ) )


	@WithSharedApplicationMockDS
	def test_wrong_user(self):
		with mock_dataserver.mock_db_trans( self.ds ):
			self._create_user()
			self._create_user('ossmkitty')

		testapp = TestApp( self.app )

		testapp.post( '/dataserver2/users/sjohnson@nextthought.com/@@accept-invitations',
					  json.dumps( {'invitation_codes': ['foobar']} ),
					  extra_environ=self._make_extra_environ(username='ossmkitty'),
					  status=403 )

	@WithSharedApplicationMockDS
	def test_valid_code(self):
		with mock_dataserver.mock_db_trans( self.ds ):
			self._create_user()

		testapp = TestApp( self.app )

		testapp.post( '/dataserver2/users/sjohnson@nextthought.com/@@accept-invitations',
					  json.dumps( {'invitation_codes': ['MATHCOUNTS']} ),
					  extra_environ=self._make_extra_environ(),
					  status=204 )

	@WithSharedApplicationMockDS
	def test_invalid_request(self):
		with mock_dataserver.mock_db_trans( self.ds ):
			self._create_user()

		testapp = TestApp( self.app )

		testapp.post( '/dataserver2/users/sjohnson@nextthought.com/@@accept-invitations',
					  json.dumps( {'invitation_codes2': ['MATHCOUNTS']} ),
					  extra_environ=self._make_extra_environ(),
					  status=400 )
