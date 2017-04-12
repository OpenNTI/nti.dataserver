#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import has_key
from hamcrest import contains
from hamcrest import has_item
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_entries
from hamcrest import greater_than
from hamcrest import has_property
from hamcrest import is_not as does_not
from hamcrest import contains_inanyorder
from hamcrest import greater_than_or_equal_to
is_not = does_not

from nti.testing.matchers import is_empty
from nti.testing.time import time_monotonically_increases

import datetime
from urllib import quote as UQ

from pyquery import PyQuery

from webob import datetime_utils

from zope import component
from zope import interface
from zope import lifecycleevent
from zope.component import eventtesting

from zope.intid.interfaces import IIntIdRemovedEvent

from nti.dataserver import users
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.tests import mock_dataserver

from nti.dataserver.contenttypes.forums.forum import PersonalBlog
from nti.dataserver.contenttypes.forums.topic import PersonalBlogEntry

from nti.ntiids import ntiids

from nti.appserver.policies.tests import test_application_censoring

from nti.app.testing.application_webtest import ApplicationLayerTest
from nti.app.testing.decorators import WithSharedApplicationMockDSHandleChanges as WithSharedApplicationMockDS

# TODO: FIXME: This solves an order-of-imports issue, where
# mimeType fields are only added to the classes when externalization is
# loaded (usually with ZCML, so in practice this is not a problem,
# but statically and in isolated unit-tests, it could be)
from nti.dataserver.contenttypes.forums import externalization as frm_ext
frm_ext = frm_ext

POST_MIME_TYPE = 'application/vnd.nextthought.forums.post'

from nti.app.forums.tests.base_forum_testing import AbstractTestApplicationForumsBaseMixin
from nti.app.forums.tests.base_forum_testing import UserCommunityFixture

class TestApplicationBlogging(AbstractTestApplicationForumsBaseMixin,ApplicationLayerTest):
	__test__ = True

	extra_environ_default_user = AbstractTestApplicationForumsBaseMixin.default_username
	forum_link_rel = 'Blog'
	forum_content_type = 'application/vnd.nextthought.forums.personalblog+json'
	forum_headline_class_type = 'Post'
	forum_topic_content_type = None
	forum_topic_ntiid_base = 'tag:nextthought.com,2011-10:' + extra_environ_default_user + '-Topic:PersonalBlogEntry-'
	forum_type = PersonalBlog
	forum_topic_comment_content_type = 'application/vnd.nextthought.forums.personalblogcomment+json'

	def setUp(self):
		super(TestApplicationBlogging,self).setUp()
		self.forum_topic_content_type = PersonalBlogEntry.mimeType + '+json'

	@WithSharedApplicationMockDS(users=True,testapp=True)
	def test_user_has_default_blog_in_service_doc( self ):

		service_doc = self.fetch_service_doc( ).json_body

		[collections] = [x['Items'] for x in service_doc['Items'] if x['Title'] == self.default_username]
		assert_that( collections, has_item( has_entry( 'Title', self.forum_link_rel ) ) )
		[blog_entry] = [x for x in collections if x['Title'] == self.forum_link_rel]
		assert_that( blog_entry, has_entry( 'href', self.forum_pretty_url ) )
		assert_that( blog_entry, has_entry( 'accepts', has_length( 2 ) ) )

		# Make sure we cannot post these things to the Pages collection
		[pages_entry] = [x for x in collections if x['Title'] == 'Pages']
		for blog_accept in blog_entry['accepts']:
			assert_that( pages_entry['accepts'], does_not( has_item( blog_accept ) ) )

	@WithSharedApplicationMockDS(users=True,testapp=True)
	def test_user_can_POST_new_blog_entry_censoring_for_coppa_user( self ):
		# There is actually no policy that allows them to create posts
		# and so this should never really kick in
		with mock_dataserver.mock_db_trans( self.ds ):
			user = users.User.get_user( self.extra_environ_default_user )
			interface.alsoProvides( user, nti_interfaces.ICoppaUser )

		# Cannot use an entirely bad title
		data = { 'Class': 'Post',
				 'title': test_application_censoring.bad_word,
				 'body': [test_application_censoring.bad_val] }

		res = self._do_test_user_can_POST_new_blog_entry( data, status_only=422 )

		assert_that( res.json_body, has_entries( 'field', 'title',
												 'message', 'The value you have used is not valid.') )
		data['title'] = data['title'] + ' abc'
		exp_data = data.copy()
		exp_data['body'] = [test_application_censoring.censored_val]
		exp_data['title'] = test_application_censoring.censored_word + ' abc'
		self._do_test_user_can_POST_new_blog_entry( data, expected_data=exp_data )


	def _do_test_user_can_POST_new_blog_entry( self, data, content_type=None, status_only=None, expected_data=None ):

		post_res = self._do_simple_tests_for_POST_of_topic_entry( data, content_type=content_type, status_only=status_only, expected_data=expected_data )
		if status_only:
			return post_res

		testapp = self.testapp
		data = expected_data or data
		res = post_res
		entry_id = res.json_body['ID']

		contents_href = self.require_link_href_with_rel( res.json_body, 'contents' )
		self.require_link_href_with_rel( res.json_body, 'like' ) # entries can be liked
		self.require_link_href_with_rel( res.json_body, 'flag' ) # entries can be flagged
		self.require_link_href_with_rel( res.json_body, 'edit' ) # entries can be 'edited' (actually they cannot, shortcut for ui)
		self.require_link_href_with_rel( res.json_body, 'favorite' ) # entries can be favorited

		entry_url = res.location
		entry_ntiid = res.json_body['NTIID']

		# The new topic is accessible at its OID URL, its pretty URL, and by NTIID
		for url in entry_url, self.forum_topic_href( entry_id ), UQ( '/dataserver2/NTIIDs/' + entry_ntiid ):
			testapp.get( url )


		# and it has no contents
		testapp.get( contents_href, status=200 )

		# It shows up in the blog contents
		res = testapp.get( self.forum_pretty_contents_url )
		blog_items = res.json_body['Items']
		assert_that( blog_items, contains( has_entry( 'title', data['title'] ) ) )
		# With its links all intact
		blog_item = blog_items[0]
		assert_that( blog_item, has_entry( 'href', self.forum_topic_href(  blog_item['ID'] ) ))
		self.require_link_href_with_rel( blog_item, 'contents' )
		self.require_link_href_with_rel( blog_item, 'like' ) # entries can be liked
		self.require_link_href_with_rel( blog_item, 'flag' ) # entries can be flagged
		self.require_link_href_with_rel( blog_item, 'edit' ) # entries can be 'edited' (actually they cannot)


		# It also shows up in the blog's data feed (partially rendered in HTML)
		res = testapp.get( self.forum_pretty_url + '/feed.atom' )
		assert_that( res.content_type, is_( 'application/atom+xml'))
		res._use_unicode = False
		pq = PyQuery( res.body, parser='html', namespaces={u'atom': u'http://www.w3.org/2005/Atom'} ) # html to ignore namespaces. Sigh.
		assert_that( pq( b'entry title' ).text(), is_( data['title'] ) )
		assert_that( pq( b'entry summary' ).text(), is_( '<div><br />' + data['body'][0] + '</div>' ) )


		# And in the user activity view
		res = self.fetch_user_activity()
		assert_that( res.json_body['Items'], contains( has_entry( 'title', data['title'] ) ) )
		assert_that( res.json_body['Items'], has_length( 1 ) ) # make sure no dups

		# And in the user root recursive data stream
		res = self.fetch_user_root_rugd(params={'filter': 'MeOnly',
												'exclude': 'application/vnd.nextthought.forums.personalblogentrypost'})
		assert_that( res.json_body, has_entry('Items',
											  contains( has_entry( 'title', data['title'] ) ) ) )

		# MVD and, if favorited, filtered to the favorites
		#testapp.post( fav_href )
		#res = self.fetch_user_root_rugd( params={'filter': 'Favorite'})
		#assert_that( res.json_body['Items'], contains( has_entry( 'title', data['title'] ) ) )
		#self.require_link_href_with_rel( res.json_body['Items'][0], 'unfavorite' )

		# And in his links
		self.require_link_href_with_rel( self.resolve_user(), 'Blog' )

		return post_res

	_do_test_user_can_POST_new_forum_entry = _do_test_user_can_POST_new_blog_entry

	@WithSharedApplicationMockDS(users=True,testapp=True)
	@time_monotonically_increases
	def test_user_can_POST_new_comment_PUT_to_edit_flag_and_DELETE( self ):
		#"""POSTing an IPost to the URL of an existing IStoryTopic adds a comment"""

		testapp = self.testapp

		# Create the blog
		data = self._create_post_data_for_POST()
		res = self._POST_topic_entry( data )
		entry_url = res.location
		entry_contents_url = self.require_link_href_with_rel( res.json_body, 'contents' )
		entry_ntiid = res.json_body['NTIID']


		# (Same user) comments on blog by POSTing a new post
		data['title'] = 'A comment'
		data['body'] = ['This is a comment body']

		res = testapp.post_json( entry_url, data, status=201 )

		assert_that( res.status_int, is_( 201 ) )
		assert_that( res.json_body, has_entry( 'title', data['title'] ) )
		assert_that( res.json_body, has_entry( 'body', data['body'] ) )
		assert_that( res.json_body, has_entry( 'ContainerId', entry_ntiid) )
		assert_that( res.location, is_( 'http://localhost' + res.json_body['href'] + '/' ) )
		# post_href = res.json_body['href']

		edit_url = self.require_link_href_with_rel( res.json_body, 'edit' )
		self.require_link_href_with_rel( res.json_body, 'like' ) # comments can be liked
		self.require_link_href_with_rel(res.json_body, 'flag')  # comments can be flagged
		data['body'] = ['Changed my body']
		data['title'] = 'Changed my title'

		res = testapp.put_json( edit_url, data )
		assert_that( res.status_int, is_( 200 ) )
		assert_that( res.json_body, has_entry( 'title', data['title'] ) )
		assert_that( res.json_body, has_entry( 'body', data['body'] ) )

		# confirm it is in the parent...
		res = testapp.get( entry_url )
		# ... metadata
		assert_that( res.json_body, has_entry( 'PostCount', 1 ) )

		# ... actual contents
		res = testapp.get( entry_contents_url )
		assert_that( res.json_body['Items'], contains( has_entry( 'title', data['title'] ) ) )
		# contents_mod_time = res.json_body['Last Modified']

		# MVD Can be flagged...
		#res = testapp.post( flag_href )
		# ...returning the same href we started with
		#assert_that( res.json_body['href'], is_( post_href ) )
		#self.require_link_href_with_rel( res.json_body, 'flag.metoo' )

		# MVD until we delete it
		#eventtesting.clearEvents()
		#res = testapp.delete( edit_url )
		#assert_that( res.status_int, is_( 204 ) )

		# When it is replaced with placeholders
		#res = testapp.get( entry_url )
		#assert_that( res.json_body, has_entry( 'PostCount', 1 ) )
		# and nothing was actually deleted yet
		#del_events = eventtesting.getEvents( lifecycleevent.IObjectRemovedEvent )
		#assert_that( del_events, has_length( 0 ) )
		#assert_that( eventtesting.getEvents( IIntIdRemovedEvent ), has_length( 0 ) )

		# But modification events did fire...
		#mod_events = eventtesting.getEvents( lifecycleevent.IObjectModifiedEvent )
		#assert_that( mod_events, has_length( 1 ) )
		# ...resulting in an updated time for the contents view
		#res = testapp.get( entry_contents_url )
		#assert_that( res.json_body['Last Modified'], is_( greater_than( contents_mod_time ) ) )


	@WithSharedApplicationMockDS(testapp=True)
	@time_monotonically_increases
	def test_user_sharing_community_can_GET_and_POST_new_comments(self):
		fixture = UserCommunityFixture( self )

		self.testapp = testapp = fixture.testapp
		testapp2 = fixture.testapp2
		testapp3 = fixture.testapp3
		user2_followerapp = fixture.user2_followerapp
		user2_follower2app = fixture.user2_follower2app
		user_username = fixture.user_username
		user2_username = fixture.user2_username
		user3_username = fixture.user3_username
		user2_follower_username = fixture.user2_follower_username
		user2_follower2_username = fixture.user2_follower2_username

		# First user creates the blog entry
		data = { 'Class': 'Post',
				 'title': 'My New Blog',
				 'body': ['My first thought'] }
		blog_data = data.copy()

		# Create the blog
		res = testapp.post_json( '/dataserver2/users/original_user@foo/Blog', blog_data )
		entry_url = res.location
		entry_ntiid = res.json_body['NTIID']
		entry_contents_url = self.require_link_href_with_rel( res.json_body, 'contents' )
		story_url = self.require_link_href_with_rel( res.json_body['headline'], 'edit' )
		pub_url = self.require_link_href_with_rel( res.json_body, 'publish' )
		fav_href = self.require_link_href_with_rel( res.json_body, 'favorite' ) # entries can be favorited

		# Before its published, the second user can see nothing
		res = testapp2.get( '/dataserver2/users/original_user@foo/Blog/contents' )
		assert_that( res.json_body['Items'], has_length( 0 ) )
		content_last_mod_ts = res.json_body['Last Modified']
		content_last_mod = datetime_utils.serialize_date(content_last_mod_ts)
		content_last_mod = datetime_utils.parse_date(content_last_mod)
		assert_that(res.last_modified, is_(content_last_mod))

		res = testapp2.get( '/dataserver2/users/original_user@foo/Blog' )
		assert_that( res.json_body, has_entry( 'TopicCount', 0 ) )

		# When it is published...
		testapp.post( pub_url )

		# Second user is able to see everything about it...
		def assert_shared_with_community( data ):
			assert_that( data,  has_entry( 'sharedWith', contains( 'TheCommunity' ) ) )

		# ...Its entry in the table-of-contents...
		res = testapp2.get( '/dataserver2/users/original_user@foo/Blog' )
		assert_that( res.json_body, has_entry( 'TopicCount', 1 ) )

		# ...Its full entry...
		res = testapp2.get( '/dataserver2/users/original_user@foo/Blog/contents' )
		assert_that( res.json_body['Items'][0], has_entry( 'title', 'My New Blog' ) )
		assert_that( res.json_body['Items'][0], has_entry( 'headline', has_entry( 'body', data['body'] ) ) )
		assert_shared_with_community( res.json_body['Items'][0] )
		# ...Which has an updated last modified...
		assert_that( res.json_body['Last Modified'], greater_than( content_last_mod_ts ) )
		content_last_mod_ts = res.json_body['Last Modified']
		content_last_mod = datetime_utils.serialize_date(content_last_mod_ts)
		content_last_mod = datetime_utils.parse_date(content_last_mod)
		assert_that(res.last_modified, is_(content_last_mod))

		# ...It can be fetched by pretty URL...
		res = testapp2.get( UQ( '/dataserver2/users/original_user@foo/Blog/My_New_Blog' ) ) # Pretty URL
		assert_that( res, has_property( 'content_type', 'application/vnd.nextthought.forums.personalblogentry+json' ) )
		assert_that( res.json_body, has_entry( 'title', 'My New Blog' ) )
		assert_that( res.json_body, has_entry( 'ID', 'My_New_Blog' ) )
		assert_that( res.json_body, has_entry( 'headline', has_entry( 'body', data['body'] ) ) )
		assert_shared_with_community( res.json_body )

		contents_href = self.require_link_href_with_rel( res.json_body, 'contents' )
		self.require_link_href_with_rel( res.json_body, 'like' ) # entries can be liked
		# MVD self.require_link_href_with_rel( res.json_body, 'flag' ) # entries can be flagged

		# MVD ...It can be fetched directly...
		# testapp2.get( entry_url )

		# MVD ...It can be seen in the activity stream for the author...
		#res = testapp2.get( '/dataserver2/users/original_user@foo/Activity' )
		#assert_that( res.json_body['Items'], contains( has_entry( 'title', data['title'] ) ) )

		# ...And in the main stream of the follower.
		res = self.fetch_user_root_rstream( testapp=testapp2, username=user2_username )
		assert_that( res.json_body['Items'], has_length( 1 ) ) # The blog entry itself
		assert_that( res.json_body['Items'][0]['Item'], has_entry( 'title', data['title'] ) )

		# (Though not the non-follower)
		# XXX: See r46562
		# self.fetch_user_root_rstream( testapp=testapp3, username=user3_username, status=404 )

		# it currently has no contents
		testapp2.get( contents_href, status=200 )

		# The other user can add comments...
		data['title'] = 'A comment'
		data['body'] = ['A comment body']
		# ...both directly...
		comment1res = testapp2.post_json( entry_url, data )
		# ...and pretty...
		data['title'] = 'Another comment'
		data['body'] = ['more comment body']
		comment2res = testapp2.post_json( UQ( '/dataserver2/users/original_user@foo/Blog/My_New_Blog' ), data )
		# (Note that although we're just sending in Posts, the location transforms them:
		assert_that( comment1res, has_property( 'content_type', 'application/vnd.nextthought.forums.personalblogcomment+json' ) )
		assert_that( comment1res.json_body, has_entry( 'MimeType', 'application/vnd.nextthought.forums.personalblogcomment' ) )
		# )

		def _has_both_comments( res, items=None ):
			items = items or res.json_body['Items']
			assert_that( items, has_length( greater_than_or_equal_to(2) ) )
			assert_that( items, has_item(
				has_entry( 'title', data['title'] ) ) )
			assert_that( items, has_item(
				has_entry( 'title', 'A comment' ) ) )

		# These created notifications to the author...
		# ... both on the socket...
		events = eventtesting.getEvents( nti_interfaces.IUserNotificationEvent )
		assert_that( events, has_length( greater_than_or_equal_to( 2 ) ) ) # possibly more due to read-conflict retries
		for evt in events:
			assert_that( evt.targets, is_( (user_username,) ) )
			#assert_that( evt.args[0], has_property( 'type', nti_interfaces.SC_CREATED ) )

		# ... and in his UGD stream ...
		res = self.fetch_user_root_rstream( username=user_username )
		_has_both_comments( res, items=[change['Item'] for change in res.json_body['Items']] )

		# ... and in the UGD stream of a user following the commentor
		res = self.fetch_user_root_rstream( testapp=user2_followerapp, username=user2_follower_username )
		_has_both_comments( res, items=[change['Item'] for change in res.json_body['Items']] )

		# (who can mute the conversation, never to see it again)
		user2_followerapp.put_json( '/dataserver2/users/' + user2_follower_username,
									 {'mute_conversation': entry_ntiid } )
		# thus removing them from his stream
		res = self.fetch_user_root_rstream( testapp=user2_followerapp, username=user2_follower_username )
		assert_that( res.json_body['Items'], has_length(1) ) # the blog entry

		# ...and in the notable data of the owner of the blog
		res = self.fetch_user_recursive_notable_ugd(testapp=testapp, username=user_username)
		_has_both_comments(res)

		# Both of these the other user can update
		data['title'] = 'Changed my title'
		data['body'] = ['A different comment body']
		data['sharedWith'] = ['a', 'b', 'c']
		res = testapp2.put_json( self.require_link_href_with_rel( comment2res.json_body, 'edit' ), data )
		comment2_fav_href = self.require_link_href_with_rel( res.json_body, 'favorite' )
		comment2_title = data['title']

		# (Though he cannot update the actual post itself)
		testapp2.put_json( story_url, data, status=403 )

		# (only the real user can do that)
		blog_data['body'] = ['Changing the blog body']
		res = testapp.put_json( story_url, blog_data, status=200 )
		assert_that( res.json_body, has_entry( 'body', blog_data['body'] ) )

		# Both visible to the original user
		res = testapp.get( entry_url )
		unpub_url = self.require_link_href_with_rel( res.json_body, 'unpublish' )
		# ... metadata
		assert_that( res.json_body, has_entry( 'PostCount', 2 ) )


		# ... actual contents
		res = testapp.get( entry_contents_url )
		_has_both_comments( res )

		for item in res.json_body['Items']:
			# sharedWith value trickles down to the comments automatically
			assert_shared_with_community( item )
			# and they each have a valid 'href'
			assert_that( item, has_key( 'href' ) )

		# ... in the blog feed for both users...
		for app in testapp, testapp2:
			res = app.get( UQ( '/dataserver2/users/original_user@foo/Blog/My_New_Blog/feed.atom' ) )
			assert_that( res.content_type, is_( 'application/atom+xml'))
			res._use_unicode = False
			pq = PyQuery( res.body, parser='html', namespaces={u'atom': u'http://www.w3.org/2005/Atom'} ) # html to ignore namespaces. Sigh.

			titles = sorted( [x.text for x in pq( b'entry title' )] )
			sums = sorted( [x.text for x in pq( b'entry summary')] )
			assert_that( titles, contains( 'A comment', 'Changed my title' ) )
			assert_that( sums, contains( '<div><br />' + 'A comment body</div>', '<div><br />' + data['body'][0] + '</div>') )

		# ... in the commenting user's activity stream, visible to all ...
		for app in testapp, testapp2, testapp3:
			res = app.get( UQ( '/dataserver2/users/' + user2_username + '/Activity' ) )
			_has_both_comments( res )

			user_activity_mod_time = res.last_modified
			user_activity_mod_time_body = res.json_body['Last Modified']

		# The original user can unpublish...
		res = testapp.post( unpub_url )
		assert_that( res.json_body, has_entry( 'sharedWith', is_empty() ) )
		# ... making it invisible to the other user ...
		# ...directly
		res = testapp2.get( '/dataserver2/users/original_user@foo/Blog/contents' )
		assert_that( res.json_body['Items'], has_length( 0 ) )
		testapp2.get( entry_url, status=403 )
		# ... and in his stream
		self.fetch_user_root_rstream( testapp=testapp2, username=user2_username, status=404 )

		# ... and the comments vanish from the stream of the other user following the commentor (the one not muted)
		self.fetch_user_root_rstream( testapp=user2_follower2app, username=user2_follower2_username, status=404 )

		# ... but the commenting user can still see his comments in his activity
		res = self.fetch_user_activity( testapp2, user2_username )
		_has_both_comments( res )
		# ... as can the original user, since he can still delete them
		res = self.fetch_user_activity( testapp, user2_username )
		_has_both_comments( res )
		# ... but the other community member cannot
		res = self.fetch_user_activity( testapp3, user2_username )
		assert_that( res.json_body['Items'], has_length( 0 ) )
		# ... and the actual blog entry is not in the activity of the creating user anymore,
		# as far as the commenting user is concerned
		res = self.fetch_user_activity( testapp2, user_username )
		assert_that( res.json_body, has_entry( 'Items', is_empty() ) )
		# All of the mod times were updated
		assert_that( res.json_body['Last Modified'], is_( greater_than( user_activity_mod_time_body ) ) )
		content_last_mod_ts = res.json_body['Last Modified']
		content_last_mod = datetime_utils.serialize_date(content_last_mod_ts)
		content_last_mod = datetime_utils.parse_date(content_last_mod)
		assert_that(res.last_modified, is_(content_last_mod))
		# and a conditional request works too

		res = testapp2.get( UQ( '/dataserver2/users/' + user_username + '/Activity' ),
						    headers={'If-Modified-Since': datetime_utils.serialize_date(user_activity_mod_time)} )
		assert_that( res.json_body, has_entry( 'Items', is_empty() ) )
		testapp2.get( UQ( '/dataserver2/users/' + user_username + '/Activity' ),
					  headers={'If-Modified-Since': datetime_utils.serialize_date(res.last_modified)},
					  status=304)


		# and it can be republished...
		res = testapp.post( pub_url )
		assert_shared_with_community( res.json_body )
		# ...making it visible again
		# directly
		res = testapp2.get( '/dataserver2/users/original_user@foo/Blog/contents' )
		assert_that( res.json_body['Items'][0], has_entry( 'title', 'My New Blog' ) )
		# in activity
		res = testapp2.get( UQ( '/dataserver2/users/' + user_username + '/Activity' ) )
		assert_that( res.json_body['Items'][0], has_entry( 'title', 'My New Blog' ) )

		res = user2_follower2app.get( '/dataserver2/users/' + user2_follower2_username + '/Pages(' + ntiids.ROOT + ')/RecursiveStream' )
		_has_both_comments( res, items=[change['Item'] for change in res.json_body['Items']] )


		# ... changing last mod date again
		assert_that( res.json_body['Last Modified'], greater_than( content_last_mod_ts ) )
		content_last_mod_ts = res.json_body['Last Modified']
		content_last_mod = datetime_utils.serialize_date(content_last_mod_ts)
		content_last_mod = datetime_utils.parse_date(content_last_mod)
		assert_that(res.last_modified, is_(content_last_mod))

		# and, if favorited, filtered to the favorites
		for uname, app in ((user_username, testapp), (user2_username, testapp2)):
			app.post( fav_href )
			res = self.fetch_user_root_rugd( app, uname, params={'filter': 'Favorite'} )
			assert_that( res.json_body['Items'], contains( has_entry( 'title', 'My New Blog' ) ) )
			unfav_href = self.require_link_href_with_rel( res.json_body['Items'][0], 'unfavorite' )

		for uname, app, status in ((user_username, testapp, 200), (user2_username, testapp2, 200)):
			app.post( unfav_href )
			res = self.fetch_user_root_rugd( app, uname, params={'filter': 'Favorite'}, status=status )
			if status == 200:
				assert_that( res.json_body['Items'], is_empty() )

		# Likewise, favoriting comments works
		for uname, app in ((user_username, testapp), (user2_username, testapp2)):
			app.post( comment2_fav_href )
			res = self.fetch_user_root_rugd( app, uname, params={'filter': 'Favorite'} )
			assert_that( res.json_body['Items'], contains( has_entry( 'title', comment2_title ) ) )
			unfav_href = self.require_link_href_with_rel( res.json_body['Items'][0], 'unfavorite' )

		for uname, app, status in ((user_username, testapp, 200), (user2_username, testapp2, 200)):
			app.post( unfav_href )
			res = self.fetch_user_root_rugd( app, uname, params={'filter': 'Favorite'}, status=status )
			if status == 200:
				assert_that( res.json_body['Items'], is_empty() )

		# The original user can delete a comment from the other user
		testapp.delete( self.require_link_href_with_rel( comment1res.json_body, 'edit' ), status=204 )
		# though he cannot edit a comment from that user
		testapp.put_json( self.require_link_href_with_rel( comment2res.json_body, 'edit' ), data, status=403 )

		# In fact, he doesn't get the link even when he asks directly
		self.forbid_link_with_rel( testapp.get( comment2res.json_body['href'] ).json_body, 'edit' )
		# But he can flag it
		flag_res = testapp.post( self.require_link_href_with_rel( comment2res.json_body, 'flag' ) )

		assert_that( flag_res.json_body['href'], is_( comment2res.json_body['href'] ) )
		self.require_link_href_with_rel( flag_res.json_body, 'flag.metoo' )

		# that comments creator can delete his own post
		testapp2.delete( self.require_link_href_with_rel( comment2res.json_body, 'edit' ), status=204 )

		# and they are now gone

		# replaced by placeholders in the contents
		res = testapp.get( entry_contents_url )
		assert_that( res.json_body['Items'], has_length( 2 ) )
		assert_that( res.json_body['Items'], contains_inanyorder(
												has_entries( 'Deleted', True,  'title', 'This item has been deleted.' ),
												has_entries( 'Deleted', True,  'title', 'This item has been deleted.' ) ) )

		# and in the metadata
		res = testapp.get( entry_url )
		assert_that( res.json_body, has_entry( 'PostCount', 2 ) )

		# Even though they still exist at the same place, they cannot be used in any way
		testapp2.delete( self.require_link_href_with_rel( comment2res.json_body, 'edit' ), status=404 )
		testapp2.get( self.require_link_href_with_rel( comment2res.json_body, 'edit' ), status=404 )
		testapp2.put_json( self.require_link_href_with_rel( comment2res.json_body, 'edit' ), data, status=404 )

		# They did get removed from the activity stream, however, for all three users
		for app in testapp, testapp2, testapp3:
			res = self.fetch_user_activity( app, user2_username )
			assert_that( res.json_body['Items'], has_length( 0 ) )

		# As well as the RecursiveStream
		for uname, app, status, length in ((user_username, testapp, 404, 0),
										   (user2_username, testapp2, 200, 1), # He still has the blog notifications
										   (user3_username, testapp3, 200, 1)): # and him too, given a change in sharing rules
			__traceback_info__ = uname
			res = app.get( '/dataserver2/users/' + uname  + '/Pages(' + ntiids.ROOT + ')/RecursiveStream', status=status )
			if status == 200:
				if length == 0:
					assert_that( res.json_body['Items'], is_empty() )
				else:
					assert_that( res.json_body['Items'], has_length(length) )


	@WithSharedApplicationMockDS
	@time_monotonically_increases
	def test_creator_can_DELETE_community_user_comment_in_published_topic(self):
		fixture = UserCommunityFixture( self )
		self.testapp = testapp = fixture.testapp
		testapp2 = fixture.testapp2

		publish_res, _ = self._POST_and_publish_topic_entry()
		topic_url = publish_res.location

		# non-creator comment
		comment_data = self._create_comment_data_for_POST()
		comment_res = testapp2.post_json( topic_url, comment_data, status=201 )
		edit_href = self.require_link_href_with_rel( comment_res.json_body, 'edit' )

		eventtesting.clearEvents()

		res = testapp.delete( edit_href )
		assert_that( res.status_int, is_( 204 ) )

		# When it is replaced with placeholders
		res = testapp2.get( topic_url )
		assert_that( res.json_body, has_entry( 'PostCount', 1 ) )
		# and nothing was actually deleted yet
		del_events = eventtesting.getEvents( lifecycleevent.IObjectRemovedEvent )
		assert_that( del_events, has_length( 0 ) )
		assert_that( eventtesting.getEvents( IIntIdRemovedEvent ), has_length( 0 ) )

		# But modification events did fire...
		mod_events = eventtesting.getEvents( lifecycleevent.IObjectModifiedEvent )
		assert_that( mod_events, has_length( 1 ) )

	@WithSharedApplicationMockDS
	@time_monotonically_increases
	def test_user_can_edit_sharing(self):
		fixture = UserCommunityFixture( self )
		self.testapp = testapp = fixture.testapp
		# testapp2 = fixture.testapp2

		# Create the blog
		data = self._create_post_data_for_POST()
		create_res = self._POST_topic_entry( data )

		# Change sharing directly
		testapp.put_json( create_res.location, {'sharedWith': [fixture.user2_username] } )
		res = testapp.get( create_res.location )
		assert_that( res.json_body, has_entry( 'sharedWith', [fixture.user2_username] ) )

		# and through the field
		testapp.put_json( create_res.location + '/++fields++sharedWith', [fixture.user3_username] )
		res = testapp.get( create_res.location )
		assert_that( res.json_body, has_entry( 'sharedWith', [fixture.user3_username] ) )


		# Publishing it changes all that
		publish_url = self.require_link_href_with_rel( create_res.json_body, 'publish' )
		testapp.post( publish_url )

		res = testapp.get( create_res.location )
		assert_that( res.json_body, has_entry( 'sharedWith', [fixture.community_name] ) )

		# Unpublishing takes us back to the default state
		unpublish_url = self.require_link_href_with_rel( res.json_body, 'unpublish' )
		testapp.post( unpublish_url )

		res = testapp.get( create_res.location )
		assert_that( res.json_body, has_entry( 'sharedWith', is_empty() ) )


	@WithSharedApplicationMockDS(users=True)
	def test_blog_display_name(self):
		from nti.dataserver.users.interfaces import IFriendlyNamed
		from nti.dataserver.contenttypes.forums.interfaces import IPersonalBlog
		from zc.displayname.interfaces import IDisplayNameGenerator
		with mock_dataserver.mock_db_trans( self.ds ):
			user = users.User.get_user( self.extra_environ_default_user )
			IFriendlyNamed(user).realname = 'Steve Johnson'

			blog = IPersonalBlog(user)

			disp_name = component.getMultiAdapter( (blog, self.beginRequest()),
												   IDisplayNameGenerator )
			disp_name = disp_name()
			assert_that(disp_name, is_("Steve Johnson's Thoughts"))
