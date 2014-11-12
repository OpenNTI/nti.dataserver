#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from zope import lifecycleevent

from hamcrest import is_
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import has_item
from hamcrest import assert_that

from nti.dataserver.users import User

from nti.dataserver.tests import mock_dataserver

from nti.app.testing.application_webtest import ApplicationLayerTest
from nti.app.testing.decorators import WithSharedApplicationMockDS

class TestBlacklistViews(ApplicationLayerTest):

	@WithSharedApplicationMockDS(users=True,testapp=True,default_authenticate=True)
	def test_blacklist_views(self):

		username = 'user_one'

		# Baseline
		path = '/dataserver2/GetUserBlacklist'
		res = self.testapp.get( path, None, status=200 )
		body = res.json_body
		assert_that( body, has_entry( 'Items', has_length( 0 )) )
		assert_that( body, has_entry( 'Count', is_( 0 )))

		with mock_dataserver.mock_db_trans( self.ds ):
			# Remove user
			user_one = User.create_user( username=username )
			lifecycleevent.removed( user_one )

		# Ok user is in our blacklist
		res = self.testapp.get( path, None, status=200 )
		body = res.json_body
		assert_that( body, has_entry( 'Items', has_length( 1 )) )
		assert_that( body, has_entry( 'Items', has_item( username )) )
		assert_that( body, has_entry( 'Count', is_( 1 )))

		# Undo
		self.testapp.post_json( '/dataserver2/RemoveFromUserBlacklist',
								{'username':username},
								status=200 )

		# Blacklist is empty
		res = self.testapp.get( path, None, status=200 )
		body = res.json_body
		assert_that( body, has_entry( 'Items', has_length( 0 )) )
		assert_that( body, has_entry( 'Count', is_( 0 )))
