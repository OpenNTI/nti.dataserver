#!/usr/bin/env python
from __future__ import print_function

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

from .test_application import TestApp

import urllib

from nti.dataserver.tests import mock_dataserver
from nti.dataserver import users
from .test_application import SharedApplicationTestBase, WithSharedApplicationMockDS
from ..dfl_views import REL_MY_MEMBERSHIP


class TestApplicationDFLViews(SharedApplicationTestBase):

	@WithSharedApplicationMockDS
	def test_link_in_dfl(self):
		with mock_dataserver.mock_db_trans( self.ds ):
			owner = self._create_user()
			owner_username = owner.username
			member_user = self._create_user( 'member@foo' )
			member_user_username = member_user.username
			other_user = self._create_user( 'otheruser@foo' )


			fl1 = users.DynamicFriendsList(username='Friends')
			fl1.creator = owner # Creator must be set
			owner.addContainedObject( fl1 )
			fl1.addFriend( member_user )
			fl1.addFriend( other_user )

			assert_that( member_user.entities_followed, contains( fl1 ) )

			dfl_ntiid = fl1.NTIID

		testapp = TestApp( self.app )

		# The member is the only one that has the link
		path = '/dataserver2/Objects/' + dfl_ntiid
		path = str(path)
		path = urllib.quote( path )

		res = testapp.get( path, extra_environ=self._make_extra_environ(member_user_username) )
		assert_that( res.json_body, has_entry( 'Links', has_item( has_entries( 'rel', REL_MY_MEMBERSHIP,
																			   'href', ends_with( '/@@' + REL_MY_MEMBERSHIP ) ) ) ) )

		res = testapp.get( path, extra_environ=self._make_extra_environ() )
		assert_that( res.json_body['Links'], does_not( has_item( has_entry( 'rel', REL_MY_MEMBERSHIP ) ) ) )

		# And the member can delete it, once
		testapp.delete( path + '/@@' + str( REL_MY_MEMBERSHIP ),
						extra_environ=self._make_extra_environ(username=member_user_username) )

		# after which it 404s
		testapp.delete( path + '/@@' + str( REL_MY_MEMBERSHIP ),
						extra_environ=self._make_extra_environ(username=member_user_username),
						status=404)

		# The member is no longer a member and no longer follows
		with mock_dataserver.mock_db_trans( self.ds ):
			owner = users.User.get_user( owner_username )
			member_user = users.User.get_user( member_user_username )
			dfl = owner.getContainedObject( fl1.containerId, fl1.id )
			assert_that( list(dfl), is_( [other_user] ) )

			assert_that( member_user.entities_followed, does_not( contains( fl1 ) ) )
