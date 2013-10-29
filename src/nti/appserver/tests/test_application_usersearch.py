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
from hamcrest import contains
from hamcrest import contains_inanyorder
from hamcrest import has_property
from hamcrest import none
from hamcrest import has_items
from hamcrest import has_length
from hamcrest import has_key
from hamcrest import is_not as does_not

from zope import interface
from zope.lifecycleevent import modified

from webtest import TestApp
from nti.dataserver import users
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.users import interfaces as user_interfaces
from nti.dataserver.tests import mock_dataserver

from nti.appserver.tests.test_application import SharedApplicationTestBase, WithSharedApplicationMockDS
from nti.appserver.account_creation_views import REL_ACCOUNT_PROFILE_SCHEMA as REL_ACCOUNT_PROFILE


class TestApplicationUserSearch(SharedApplicationTestBase):

	@WithSharedApplicationMockDS
	def test_user_search_has_dfl(self):


		with mock_dataserver.mock_db_trans(self.ds):
			user1 = self._create_user()
			user2 = self._create_user(username='jason@nextthought.com' )
			dfl = users.DynamicFriendsList( username='Friends' )
			dfl.creator = user1
			user1.addContainedObject( dfl )
			dfl.addFriend( user2 )
			dfl_ntiid = dfl.NTIID

		testapp = TestApp( self.app )
		# We can search for ourself
		path = '/dataserver2/UserSearch/sjohnson@nextthought.com'
		res = testapp.get( path, extra_environ=self._make_extra_environ())

		ourself = res.json_body['Items'][0]
		assert_that( ourself, has_entry( 'Username', 'sjohnson@nextthought.com' ) )

		# we can search for our FL
		path = '/dataserver2/UserSearch/Friends'
		res = testapp.get( path, extra_environ=self._make_extra_environ())
		assert_that( res.json_body['Items'], has_item( has_entry( 'realname', 'Friends' ) ) )
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

			assert_that( res.json_body, has_entry( 'Items', has_length( 1 ) ) )
			member = res.json_body['Items'][0]
			assert_that( member, has_entry( 'Username', dfl_ntiid ) )

		# UserSearch does prefix match, resolve is exact
		for t, cnt in (("UserSearch",1), ('ResolveUser',0) ):
			path = '/dataserver2/%s/Friend' % t
			res = testapp.get( str(path), extra_environ=self._make_extra_environ('jason@nextthought.com'))
			assert_that( res.json_body['Items'], has_length( cnt ) )

		# The prefix match of usersearch can find the community as well
		path = '/dataserver2/UserSearch/f'
		res = testapp.get( str(path), extra_environ=self._make_extra_environ('jason@nextthought.com'))
		assert_that( res.json_body['Items'], has_length( 1 ) )
		assert_that( res.json_body['Items'], has_items(
														has_entry( 'alias', 'Friends' ) ) )

	@WithSharedApplicationMockDS
	def test_user_search(self):

		with mock_dataserver.mock_db_trans(self.ds):
			user = self._create_user()
			user_interfaces.IFriendlyNamed( user ).realname = u"Steve Johnson"

		testapp = TestApp( self.app )
		res = testapp.get( '/dataserver2', extra_environ=self._make_extra_environ())
		# The service doc contains a link
		assert_that( res.json_body['Items'], has_item( all_of(
															has_entry( 'Title', 'Global' ),
															has_entry( 'Links', has_item( has_entry( 'href', '/dataserver2/UserSearch' ) ) ) ) ) )

		# We can search for ourself
		path = '/dataserver2/UserSearch/sjohnson@nextthought.com'
		res = testapp.get( path, extra_environ=self._make_extra_environ())

		assert_that( res.content_type, is_( 'application/vnd.nextthought+json' ) )
		assert_that( res.last_modified, is_( none() ) )

		assert_that( res.body, contains_string( str('sjohnson@nextthought.com') ) )

		sj = res.json_body['Items'][0]
		# We should have an edit link when we find ourself
		assert_that( sj, has_entry( 'Links',
									has_item(
										all_of(
											has_entry( 'href', "/dataserver2/users/sjohnson%40nextthought.com" ),
											has_entry( 'rel', 'edit' ) ) ) ) )
		# also the impersonate link
		assert_that( sj, has_entry( 'Links',
									has_item(
										all_of(
											has_entry( 'href', "/dataserver2/logon.nti.impersonate" ),
											has_entry( 'rel', 'logon.nti.impersonate' ) ) ) ) )

		# We should have our name
		assert_that( sj, has_entry( 'realname', 'Steve Johnson' ) )
		assert_that( sj, has_entry( 'NonI18NFirstName', 'Steve' ) )
		assert_that( sj, has_entry( 'NonI18NLastName', 'Johnson' ) )


	@WithSharedApplicationMockDS
	def test_user_search_subset(self):
		with mock_dataserver.mock_db_trans(self.ds):
			user = self._create_user()
			user2 = self._create_user( username=user.username + '2' )
			# have to share a damn community
			community = users.Community.create_community( username='TheCommunity' )
			user.record_dynamic_membership( community )
			user2.record_dynamic_membership( community )

		testapp = TestApp( self.app )
		# We can resolve just ourself
		path = '/dataserver2/ResolveUser/sjohnson@nextthought.com'
		res = testapp.get( path, extra_environ=self._make_extra_environ())
		assert_that( res.json_body['Items'], has_length( 1 ) )
		self.require_link_href_with_rel( res.json_body['Items'][0], 'Activity' )

		# We can search for ourself and the other user
		path = '/dataserver2/UserSearch/sjohnson@nextthought.com'
		res = testapp.get( path, extra_environ=self._make_extra_environ())
		assert_that( res.json_body['Items'], has_length( 2 ) )

	@WithSharedApplicationMockDS
	def test_user_search_username_is_prefix(self):
		with mock_dataserver.mock_db_trans(self.ds):
			user = self._create_user()
			user_username = user.username
			user2 = self._create_user( username=user.username + '2' )
			user2_username = user2.username
			# A user after it, alphabetically
			user3 = self._create_user( username='z' + user.username )
			user3_username = user3.username
			# A user before it, alphabetically
			user4 = self._create_user( username='a' + user.username )
			user4_username = user4.username
			# have to share a damn community...which incidentally comes
			# after user2 but before user3
			community = users.Community.create_community( username='TheCommunity' )
			for u in user, user2, user3, user4:
				u.record_dynamic_membership( community )

		testapp = TestApp( self.app )
		# We can always resolve just ourself
		path = '/dataserver2/ResolveUser/sjohnson@nextthought.com'
		res = testapp.get( path, extra_environ=self._make_extra_environ())
		assert_that( res.json_body['Items'], has_length( 1 ) )
		assert_that( res.json_body['Items'], contains( has_entry( 'Username', user_username ) ) )

		# We can search for ourself and the other user that shares the common prefix
		path = '/dataserver2/UserSearch/sjohnson@nextthought.com'
		res = testapp.get( path, extra_environ=self._make_extra_environ())
		assert_that( res.json_body['Items'], has_length( 2 ) )
		assert_that( res.json_body['Items'], contains_inanyorder( has_entry( 'Username', user_username ),
																  has_entry( 'Username', user2_username ) ) )

		# We can search for the entry before us and only find it
		path = '/dataserver2/UserSearch/' + user4_username
		res = testapp.get( path, extra_environ=self._make_extra_environ())
		assert_that( res.json_body['Items'], has_length( 1 ) )
		assert_that( res.json_body['Items'], contains( has_entry( 'Username', user4_username ) ) )

	@WithSharedApplicationMockDS
	def test_user_search_communities(self):
		with mock_dataserver.mock_db_trans(self.ds):
			u1 = self._create_user()
			user_interfaces.IFriendlyNamed( u1 ).realname = u"sjo"
			modified( u1 )
			u2 = self._create_user( username='sjo2@nextthought.com' )
			u3 = self._create_user( username='sjo3@nextthought.com' )
			community = users.Community.create_community( username='TheCommunity' )
			u1.record_dynamic_membership( community )
			u2.record_dynamic_membership( community )

		testapp = TestApp( self.app )

		# We can search for ourself
		path = '/dataserver2/UserSearch/sjo'
		res = testapp.get( path, extra_environ=self._make_extra_environ())

		# We only matched the two that were in the same community
		assert_that( res.json_body['Items'], has_length( 2 ) )
		assert_that( res.json_body['Items'], has_item( has_entry( 'Username', 'sjohnson@nextthought.com' ) ) )
		assert_that( res.json_body['Items'], has_item( has_entry( 'Username', 'sjo2@nextthought.com' ) ) )

		# Getting a 'Class' value back here really confuses the iPad
		assert_that( res.json_body, does_not( has_key( 'Class' ) ) )

		# We can search for the community by prefix...
		path = '/dataserver2/UserSearch/TheComm'
		res = testapp.get( path, extra_environ=self._make_extra_environ())
		assert_that( res.json_body['Items'], has_length( 1 ) )

		# ... but not by substring
		path = '/dataserver2/UserSearch/Comm'
		res = testapp.get( path, extra_environ=self._make_extra_environ())
		assert_that( res.json_body['Items'], has_length( 0 ) )


		# The user that's not in the community cannot
		res = testapp.get( path, extra_environ=self._make_extra_environ(username=u3.username))
		assert_that( res.json_body['Items'], has_length( 0 ) )

	@WithSharedApplicationMockDS
	def test_user_search_mathcounts_policy(self):
		"On the mathcounts site, we cannot search for realname or alias"
		with mock_dataserver.mock_db_trans(self.ds):
			u1 = self._create_user()
			interface.alsoProvides( u1, nti_interfaces.ICoppaUser )
			modified( u1 ) # update catalog
			u2 = self._create_user( username='sj2@nextthought.com' )
			user_interfaces.IFriendlyNamed( u2 ).alias = u"Steve"
			user_interfaces.IFriendlyNamed( u2 ).realname = u"Steve Jay Johnson"
			modified( u2 )
			community = users.Community.create_community( username='TheCommunity' )
			u1.record_dynamic_membership( community )
			u2.record_dynamic_membership( community )

		testapp = TestApp( self.app )


		# On a regular site, we can search by alias or realname (Normal search works)
		path = '/dataserver2/UserSearch/steve' # alias
		res = testapp.get( path, extra_environ=self._make_extra_environ())
		assert_that( res.json_body['Items'], has_length( 1 ) )
		assert_that( res.json_body['Items'], has_item( has_entry( 'Username', 'sj2@nextthought.com' ) ) )
		assert_that( res.json_body['Items'], has_item( has_entry( 'alias', 'Steve' ) ) )
		assert_that( res.json_body['Items'], has_item( has_entry( 'realname', 'Steve Jay Johnson' ) ) )

		path = '/dataserver2/UserSearch/JAY' # realname
		res = testapp.get( path, extra_environ=self._make_extra_environ())
		assert_that( res.json_body['Items'], has_length( 1 ) )
		assert_that( res.json_body['Items'], has_item( has_entry( 'Username', 'sj2@nextthought.com' ) ) )
		assert_that( res.json_body['Items'], has_item( has_entry( 'alias', 'Steve' ) ) )
		assert_that( res.json_body['Items'], has_item( has_entry( 'realname', 'Steve Jay Johnson' ) ) )


		# MC search is locked down to be only the username
		path = '/dataserver2/UserSearch/steve' # alias
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

		# But if the hit was us, we get back some special links to the privacy policy
		environ['HTTP_ORIGIN'] = 'http://mathcounts.nextthought.com'
		res = testapp.get( b'/dataserver2/UserSearch/' + str(u1.username), extra_environ=environ )
		assert_that( res.json_body['Items'], has_length( 1 ) )
		found = res.json_body['Items'][0]
		self.require_link_href_with_rel( found, 'childrens-privacy' )

		prof = self.require_link_href_with_rel( found, REL_ACCOUNT_PROFILE )
		# At one time, we were double-nesting this link, hence the path check
		assert_that( prof, is_( '/dataserver2/users/sjohnson%40nextthought.com/@@' + REL_ACCOUNT_PROFILE  ) )

	@WithSharedApplicationMockDS(users=True,testapp=True)
	def test_search_empty_200(self):
		"Searching with an empty term returns empty results"
		# The results are not defined across the search types,
		# we just test that it doesn't raise a 404
		self.testapp.get( '/dataserver2/UserSearch/', status=200 )

	@WithSharedApplicationMockDS(users=True,testapp=True)
	def test_resolve_empty_404(self):
		# Resolving an empty string raises a 404
		self.resolve_user_response(username='', status=404)

	@WithSharedApplicationMockDS(users=True,testapp=True)
	def test_self_resolve(self):
		# Resolving ourself uses a different caching strategy
		res = self.resolve_user_response()
		assert_that( res.cache_control, has_property( 'max_age', 0 ) )
