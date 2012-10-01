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
from hamcrest import none
from hamcrest import has_length
from hamcrest import has_key
from hamcrest import is_not as does_not

from webtest import TestApp
from nti.dataserver import users
from nti.dataserver.users import interfaces as user_interfaces
from nti.dataserver.tests import mock_dataserver

from nti.appserver.tests.test_application import ApplicationTestBase

class TestApplicationUserSearch(ApplicationTestBase):

	def test_user_search_has_dfl(self):
		with mock_dataserver.mock_db_trans(self.ds):
			user1 = self._create_user()
			user2 = self._create_user(username='jason@nextthought.com' )
			dfl = users.DynamicFriendsList( username='Friends' )
			dfl.creator = user1
			dfl.addFriend( user2 )
			user1.addContainedObject( dfl )
			dfl_ntiid = dfl.NTIID

		testapp = TestApp( self.app )
		# We can search for ourself
		path = '/dataserver2/UserSearch/sjohnson@nextthought.com'
		res = testapp.get( path, extra_environ=self._make_extra_environ())

		ourself = res.json_body['Items'][0]
		assert_that( ourself, has_entry( 'Username', 'sjohnson@nextthought.com' ) )
		#assert_that( ourself, has_entry( 'FriendsLists', has_key( 'Friends' ) ) )


		# We can search for the member, and we'll find our DFL listed in his
		# communities

		path = '/dataserver2/UserSearch/jason@nextthought.com'
		res = testapp.get( path, extra_environ=self._make_extra_environ('jason@nextthought.com'))

		member = res.json_body['Items'][0]
		assert_that( member, has_entry( 'Username', 'jason@nextthought.com' ) )
		assert_that( member, has_entry( 'Communities', has_item( has_entry( 'Username', dfl_ntiid ) ) ) )

		# We can also search for the DFL, by its lowercase NTIID
		# The application for some reason is lowercasing the Username, which is WRONG.
		# It should take what the DS gives it.
		# TODO: The security on this isn't very tight
		path = '/dataserver2/ResolveUser/' + dfl_ntiid.lower()
		res = testapp.get( str(path), extra_environ=self._make_extra_environ('sjohnson@nextthought.com'))

		member = res.json_body['Items'][0]
		assert_that( member, has_entry( 'Username', dfl_ntiid ) )

		# And we can also search for their display names. Sigh.
		for t in ("UserSearch", 'ResolveUser' ):
			path = '/dataserver2/%s/Friends' % t
			res = testapp.get( str(path), extra_environ=self._make_extra_environ('jason@nextthought.com'))

			member = res.json_body['Items'][0]
			assert_that( member, has_entry( 'Username', dfl_ntiid ) )

		# UserSearch does substring match, resolve is exact
		for t, cnt in (("UserSearch",1), ('ResolveUser',0) ):
			path = '/dataserver2/%s/Friend' % t
			res = testapp.get( str(path), extra_environ=self._make_extra_environ('jason@nextthought.com'))
			assert_that( res.json_body['Items'], has_length( cnt ) )


	def test_user_search(self):
		with mock_dataserver.mock_db_trans(self.ds):
			user = self._create_user()
			user_interfaces.IFriendlyNamed( user ).realname = u"Steve Johnson"

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

		# We should have our name
		assert_that( res.json_body['Items'][0], has_entry( 'realname', 'Steve Johnson' ) )

	def test_user_search_subset(self):
		with mock_dataserver.mock_db_trans(self.ds):
			user = self._create_user()
			user2 = self._create_user( username=user.username + '2' )
			# have to share a damn community
			community = users.Community.create_community( username='TheCommunity' )
			user.join_community( community )
			user2.join_community( community )

		testapp = TestApp( self.app )
		# We can resolve just ourself
		path = '/dataserver2/ResolveUser/sjohnson@nextthought.com'
		res = testapp.get( path, extra_environ=self._make_extra_environ())
		assert_that( res.json_body['Items'], has_length( 1 ) )

		path = '/dataserver2/UserSearch/sjohnson@nextthought.com'
		res = testapp.get( path, extra_environ=self._make_extra_environ())
		assert_that( res.json_body['Items'], has_length( 2 ) )

	def test_user_search_communities(self):
		with mock_dataserver.mock_db_trans(self.ds):
			u1 = self._create_user()
			user_interfaces.IFriendlyNamed( u1 ).realname = u"sj"
			u2 = self._create_user( username='sj2@nextthought.com' )
			u3 = self._create_user( username='sj3@nextthought.com' )
			community = users.Community.create_community( username='TheCommunity' )
			u1.join_community( community )
			u2.join_community( community )

		testapp = TestApp( self.app )

		# We can search for ourself
		path = '/dataserver2/UserSearch/sj'
		res = testapp.get( path, extra_environ=self._make_extra_environ())

		# We only matched the two that were in the same community
		assert_that( res.json_body['Items'], has_length( 2 ) )
		assert_that( res.json_body['Items'], has_item( has_entry( 'Username', 'sjohnson@nextthought.com' ) ) )
		assert_that( res.json_body['Items'], has_item( has_entry( 'Username', 'sj2@nextthought.com' ) ) )

		# Getting a 'Class' value back here really confuses the iPad
		assert_that( res.json_body, does_not( has_key( 'Class' ) ) )

		# We can search for the community
		path = '/dataserver2/UserSearch/Community'
		res = testapp.get( path, extra_environ=self._make_extra_environ())
		assert_that( res.json_body['Items'], has_length( 1 ) )

		# The user that's not in the community cannot
		res = testapp.get( path, extra_environ=self._make_extra_environ(username=u3.username))
		assert_that( res.json_body['Items'], has_length( 0 ) )

	def test_user_search_mathcounts_policy(self):
		"On the mathcounts site, we cannot search for realname or alias"
		with mock_dataserver.mock_db_trans(self.ds):
			u1 = self._create_user()
			u2 = self._create_user( username='sj2@nextthought.com' )
			user_interfaces.IFriendlyNamed( u2 ).alias = u"Steve"
			user_interfaces.IFriendlyNamed( u2 ).realname = u"Steve Johnson"
			community = users.Community.create_community( username='TheCommunity' )
			u1.join_community( community )
			u2.join_community( community )

		testapp = TestApp( self.app )


		# Normal search works
		path = '/dataserver2/UserSearch/steve'
		res = testapp.get( path, extra_environ=self._make_extra_environ())
		assert_that( res.json_body['Items'], has_length( 1 ) )
		assert_that( res.json_body['Items'], has_item( has_entry( 'Username', 'sj2@nextthought.com' ) ) )
		assert_that( res.json_body['Items'], has_item( has_entry( 'alias', 'Steve' ) ) )
		assert_that( res.json_body['Items'], has_item( has_entry( 'realname', 'Steve Johnson' ) ) )

		# MC search is locked down to be only the username
		environ = self._make_extra_environ()
		environ['HTTP_ORIGIN'] = 'http://mathcounts.nextthought.com'
		res = testapp.get( path, extra_environ=environ )
		assert_that( res.json_body['Items'], has_length( 0 ) )

		# Even if it does find a hit, we don't get back a realname and the alias is set to the username
		environ = self._make_extra_environ()
		environ['HTTP_ORIGIN'] = 'http://mathcounts.nextthought.com'
		res = testapp.get( b'/dataserver2/UserSearch/sj2@nextthought.com', extra_environ=environ )
		assert_that( res.json_body['Items'], has_length( 1 ) )
		assert_that( res.json_body['Items'], has_item( has_entry( 'alias', 'sj2@nextthought.com' ) ) )
		assert_that( res.json_body['Items'], has_item( has_entry( 'realname', none() ) ) )


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
