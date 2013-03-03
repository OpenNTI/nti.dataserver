#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""


$Id$
"""

from __future__ import print_function, unicode_literals, absolute_import
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

#disable: accessing protected members, too many methods
#pylint: disable=W0212,R0904


from hamcrest import assert_that
from hamcrest import has_property
from hamcrest import is_
from hamcrest import is_not as does_not
is_not = does_not
from hamcrest import has_item
from hamcrest import contains
from hamcrest import contains_inanyorder
from hamcrest import contains_string
from hamcrest import has_length
from hamcrest import has_entry
from hamcrest import has_entries
from nti.tests import is_empty
from .test_application import TestApp

from zope import lifecycleevent
from zope.component import eventtesting
from zope.intid.interfaces import IIntIdRemovedEvent
from zope.location.interfaces import ISublocations

import simplejson as json

from nti.ntiids import ntiids
from nti.dataserver import users
from nti.dataserver import interfaces as nti_interfaces
from nti.chatserver import interfaces as chat_interfaces
from nti.dataserver.tests import mock_dataserver

from nti.dataserver.contenttypes.forums.forum import PersonalBlog
from nti.dataserver.contenttypes.forums.post import Post

from .test_application import SharedApplicationTestBase, WithSharedApplicationMockDS, PersistentContainedExternal

from urllib import quote as UQ
from pyquery import PyQuery

class TestApplicationBlogging(SharedApplicationTestBase):

	@WithSharedApplicationMockDS(users=True,testapp=True)
	def test_user_has_default_blog_in_service_doc( self ):
		testapp = self.testapp
		res = testapp.get( '/dataserver2/' )
		service_doc = res.json_body
		[collections] = [x['Items'] for x in service_doc['Items'] if x['Title'] == 'sjohnson@nextthought.com']
		assert_that( collections, has_item( has_entry( 'Title', 'Blog' ) ) )
		[blog_entry] = [x for x in collections if x['Title'] == 'Blog']
		assert_that( blog_entry, has_entry( 'href', '/dataserver2/users/sjohnson%40nextthought.com/Blog' ) )
		assert_that( blog_entry, has_entry( 'accepts', has_length( 2 ) ) )

		# Make sure we cannot post these things to the Pages collection
		[pages_entry] = [x for x in collections if x['Title'] == 'Pages']
		for blog_accept in blog_entry['accepts']:
			assert_that( pages_entry['accepts'], does_not( has_item( blog_accept ) ) )


	@WithSharedApplicationMockDS(users=True,testapp=True)
	def test_user_has_default_blog( self ):
		testapp = self.testapp

		# The blog can be found at a pretty url, and by NTIID
		pretty_url = '/dataserver2/users/sjohnson@nextthought.com/Blog'
		ntiid_url = '/dataserver2/NTIIDs/tag:nextthought.com,2011-10:sjohnson@nextthought.com-Forum:PersonalBlog-Blog'
		for url in pretty_url, ntiid_url:
			res = testapp.get( url )

			assert_that( res, has_property( 'content_type', 'application/vnd.nextthought.forums.personalblog+json' ) )
			assert_that( res.json_body, has_entry( 'title', 'sjohnson@nextthought.com' ) )

			# We have a contents URL
			contents_href = self.require_link_href_with_rel( res.json_body, 'contents' )
			# Make sure we're getting back pretty URLs
			assert_that( contents_href, is_( UQ( '/dataserver2/users/sjohnson@nextthought.com/Blog/contents' ) ))
			# which is empty...
			testapp.get( contents_href, status=200 )

			# ...And thus not in my links
			res = testapp.get( '/dataserver2/ResolveUser/sjohnson@nextthought.com' )
			assert_that( res.json_body['Items'][0]['Links'], does_not( has_item( has_entry( 'rel', 'Blog' ) ) ) )



	@WithSharedApplicationMockDS(users=True,testapp=True)
	def test_user_cannot_POST_new_blog_entry_to_pages( self ):
		"""POSTing an IPost to the default user URL does nothing"""

		testapp = self.testapp

		data = { 'Class': 'Post',
				 'title': 'My New Blog',
				 'body': ['My first thought'] }

		# No containerId
		testapp.post_json( '/dataserver2/users/sjohnson@nextthought.com', data, status=422 )
		testapp.post_json( '/dataserver2/users/sjohnson@nextthought.com/Pages', data, status=422 )

		data['ContainerId'] = 'tag:foo:bar'
		testapp.post_json( '/dataserver2/users/sjohnson@nextthought.com', data, status=422 )
		res = testapp.post_json( '/dataserver2/users/sjohnson@nextthought.com/Pages', data, status=422 )

		assert_that( res.json_body, has_entry( 'code', 'InvalidContainerType' ) )
		assert_that( res.json_body, has_entry( 'field', 'ContainerId' ) )
		assert_that( res.json_body, has_entry( 'message', is_not( is_empty() ) ) )


	@WithSharedApplicationMockDS(users=True,testapp=True)
	def test_user_can_POST_new_blog_entry_class( self ):
		"""POSTing an IPost to the blog URL automatically creates a new topic"""

		# With a Class value:
		data = { 'Class': 'Post',
				 'title': 'My New Blog',
				 'body': ['My first thought'] }

		self._do_test_user_can_POST_new_blog_entry( data )

	@WithSharedApplicationMockDS(users=True,testapp=True)
	def test_user_can_POST_new_blog_entry_mime_type_only( self ):


		data = { 'Class': 'Post',
				 'title': 'My New Blog',
				 'body': ['My first thought'] }

		# With only a MimeType value:
		del data['Class']
		data['MimeType'] = Post.mimeType
		self._do_test_user_can_POST_new_blog_entry( data )

	@WithSharedApplicationMockDS(users=True,testapp=True)
	def test_user_can_POST_new_blog_entry_both( self ):

		# With a Class value:
		data = { 'Class': 'Post',
				 'title': 'My New Blog',
				 'body': ['My first thought'] }

		# With both
		data['Class'] = 'Post'
		data['MimeType'] = Post.mimeType
		self._do_test_user_can_POST_new_blog_entry( data )

	@WithSharedApplicationMockDS(users=True,testapp=True)
	def test_user_can_POST_new_blog_entry_header( self ):

		# With a Class value:
		data = { 'Class': 'Post',
				 'title': 'My New Blog',
				 'body': ['My first thought'] }


		# With neither, but a content-type header
		del data['Class']

		self._do_test_user_can_POST_new_blog_entry( data, content_type=Post.mimeType )


	def _do_test_user_can_POST_new_blog_entry( self, data, content_type=None ):
		testapp = self.testapp

		if not content_type:
			res = testapp.post_json( '/dataserver2/users/sjohnson@nextthought.com/Blog', data, status=201 )
		else:
			# testapp.post_json forces the content-type header
			res = testapp.post(  '/dataserver2/users/sjohnson@nextthought.com/Blog',
								 json.dumps( data ),
								 headers={b'Content-Type': str(Post.mimeType)},
								 status=201 )

		# Return the representation of the new topic created
		assert_that( res, has_property( 'content_type', 'application/vnd.nextthought.forums.personalblogentry+json' ) )
		assert_that( res.json_body, has_entry( 'title', 'My New Blog' ) )
		assert_that( res.json_body, has_entry( 'headline', has_entry( 'body', data['body'] ) ) )
		assert_that( res.json_body, has_entry( 'NTIID', 'tag:nextthought.com,2011-10:sjohnson@nextthought.com-Topic:PersonalBlogEntry-My New Blog' ) )
		assert_that( res.json_body, has_entry( 'ContainerId', 'tag:nextthought.com,2011-10:sjohnson@nextthought.com-Forum:PersonalBlog-Blog') )
		assert_that( res.json_body, has_entry( 'href', UQ( '/dataserver2/users/sjohnson@nextthought.com/Blog/' + data['title'] ) ))
		contents_href = self.require_link_href_with_rel( res.json_body, 'contents' )
		self.require_link_href_with_rel( res.json_body, 'like' ) # entries can be liked
		self.require_link_href_with_rel( res.json_body, 'flag' ) # entries can be flagged
		self.require_link_href_with_rel( res.json_body, 'edit' ) # entries can be 'edited' (actually they cannot)
		entry_url = res.location
		entry_ntiid = res.json_body['NTIID']

		# The new topic is accessible at its OID URL, its pretty URL, and by NTIID
		for url in entry_url, UQ( '/dataserver2/users/sjohnson@nextthought.com/Blog/My New Blog' ), UQ( '/dataserver2/NTIIDs/' + entry_ntiid ):
			testapp.get( url )


		# and it has no contents
		testapp.get( contents_href, status=200 )

		# It shows up in the blog contents
		res = testapp.get( '/dataserver2/users/sjohnson@nextthought.com/Blog/contents' )
		blog_items = res.json_body['Items']
		assert_that( blog_items, contains( has_entry( 'title', data['title'] ) ) )
		# With its links all intact
		blog_item = blog_items[0]
		assert_that( blog_item, has_entry( 'href', UQ( '/dataserver2/users/sjohnson@nextthought.com/Blog/' + data['title'] ) ))
		self.require_link_href_with_rel( blog_item, 'contents' )
		self.require_link_href_with_rel( blog_item, 'like' ) # entries can be liked
		self.require_link_href_with_rel( blog_item, 'flag' ) # entries can be flagged
		self.require_link_href_with_rel( blog_item, 'edit' ) # entries can be 'edited' (actually they cannot)


		# It also shows up in the blog's data feed
		res = testapp.get( '/dataserver2/users/sjohnson@nextthought.com/Blog/feed.atom' )
		assert_that( res.content_type, is_( 'application/atom+xml'))
		res._use_unicode = False
		pq = PyQuery( res.body, parser='html', namespaces={u'atom': u'http://www.w3.org/2005/Atom'} ) # html to ignore namespaces. Sigh.
		assert_that( pq( b'entry title' ).text(), is_( 'My New Blog' ) )
		assert_that( pq( b'entry summary' ).text(), is_( 'My first thought' ) )


		# And in the user activity view
		res = testapp.get( '/dataserver2/users/sjohnson@nextthought.com/Activity' )
		assert_that( res.json_body['Items'], contains( has_entry( 'title', data['title'] ) ) )
		assert_that( res.json_body['Items'], has_length( 1 ) ) # make sure no dups

		# And in the user root recursive data stream
		res = testapp.get( '/dataserver2/users/sjohnson@nextthought.com/Pages(' + ntiids.ROOT + ')/RecursiveUserGeneratedData' )
		assert_that( res.json_body['Items'], contains( has_entry( 'title', data['title'] ) ) )

		# And in his links
		res = testapp.get( '/dataserver2/ResolveUser/sjohnson@nextthought.com' )
		self.require_link_href_with_rel( res.json_body['Items'][0], 'Blog' )

	@WithSharedApplicationMockDS(users=True,testapp=True)
	def test_user_can_POST_new_blog_entry_resulting_in_blog_being_sublocation( self ):
		"""Creating a Blog causes it to be a sublocation of the user"""
		# This way deleting/moving the user correctly causes the blog to be deleted/moved

		testapp = self.testapp

		data = { 'Class': 'Post',
				 'title': 'My New Blog',
				 'body': ['My first thought'] }

		res = testapp.post_json( '/dataserver2/users/sjohnson@nextthought.com/Blog', data, status=201 )

		with mock_dataserver.mock_db_trans( self.ds ):
			user = users.User.get_user( 'sjohnson@nextthought.com' )

			all_subs = set()
			def _recur( i ):
				all_subs.add( i )
				subs = ISublocations( i, None )
				if subs:
					for x in subs.sublocations():
						_recur( x )
			_recur( user )

			assert_that( all_subs, has_item( is_( PersonalBlog ) ) )


	@WithSharedApplicationMockDS(users=True,testapp=True)
	def test_user_can_PUT_to_edit_existing_blog_entry( self ):
		"""PUTting an IPost to the 'headline' of a blog entry edits the story"""

		testapp = self.testapp

		data = { 'Class': 'Post',
				 'title': 'My New Blog',
				 'body': ['My first thought'] }

		res = testapp.post_json( '/dataserver2/users/sjohnson@nextthought.com/Blog', data )
		entry_url = res.location
		# I can PUT directly to the object URL
		story_url = self.require_link_href_with_rel( res.json_body['headline'], 'edit' )

		data['body'] = ['An updated body']

		testapp.put_json( story_url, data )

		# And check it by getting the whole container
		res = testapp.get( entry_url )
		assert_that( res.json_body, has_entry( 'headline', has_entry( 'body', data['body'] ) ) )

		# Changing the title changes the title of the container, but NOT the url or ID of anything
		data['title'] = 'A New Title'
		testapp.put_json( story_url, data )
		res = testapp.get( entry_url )
		assert_that( res.json_body, has_entry( 'headline', has_entry( 'title', data['title'] ) ) )
		assert_that( res.json_body, has_entry( 'title', data['title'] ) )

		# Pretty URL did not change
		testapp.get( UQ( '/dataserver2/users/sjohnson@nextthought.com/Blog/My New Blog' ) )

		# I can also PUT to the pretty path to the object
		data['body'] = ['An even newer body']

		testapp.put_json( UQ( '/dataserver2/users/sjohnson@nextthought.com/Blog/My New Blog/headline' ), data )
		res = testapp.get( entry_url )
		assert_that( res.json_body, has_entry( 'headline', has_entry( 'body', data['body'] ) ) )

		# And I can use the 'fields' URL to edit just parts of it, including title and body
		for field in 'body', 'title':
			data[field] = 'Edited with fields'
			if field == 'body': data[field] = [data[field]]

			testapp.put_json( story_url + '/++fields++' + field, data[field] )
			res = testapp.get( entry_url )
			assert_that( res.json_body, has_entry( 'headline', has_entry( field, data[field] ) ) )

	@WithSharedApplicationMockDS(users=True,testapp=True)
	def test_user_cannot_change_sharing_on_blog_entry( self ):
		""" Sharing is fixed and cannot be changed for a blog entry, its story, or a comment"""

		testapp = self.testapp

		data = { 'Class': 'Post',
				 'title': 'My New Blog',
				 'body': ['My first thought'] }

		res = testapp.post_json( '/dataserver2/users/sjohnson@nextthought.com/Blog', data )
		entry_url = res.location
		story_url = self.require_link_href_with_rel( res.json_body['headline'], 'edit' )

		eventtesting.clearEvents()

		# Field updates
		# Cannot change the entry
		testapp.put_json( entry_url + '/++fields++sharedWith',
						  ['Everyone'],
						  # Because of the way traversal is right now, this results in a 404,
						  # when really we want a 403
						  status=404)

		# Cannot change the story
		testapp.put_json( story_url + '/++fields++sharedWith',
						  ['Everyone'],
						  status=404) # same as above


		# Nor when putting the whole thing
		# The entry itself simply cannot be modified (predicate mismatch right now)
		testapp.put_json( entry_url,
						  {'sharedWith': ['Everyone']},
						  status=404 )

		# The story accepts it but ignores it
		res = testapp.put_json( story_url,
								{'sharedWith': ['Everyone']},
								status=200 )
		assert_that( res.json_body, has_entry( 'sharedWith', is_empty() ) )

		res = testapp.get( story_url )
		assert_that( res.json_body, has_entry( 'sharedWith', is_empty() ) )

	@WithSharedApplicationMockDS(users=True,testapp=True)
	def test_user_can_DELETE_existing_blog_entry( self ):
		"""A StoryTopic can be deleted from its object URL"""

		testapp = self.testapp

		data = { 'Class': 'Post',
				 'title': 'My New Blog',
				 'body': ['My first thought'] }

		res = testapp.post_json( '/dataserver2/users/sjohnson@nextthought.com/Blog', data )
		entry_url = res.location
		story_url = self.require_link_href_with_rel( res.json_body['headline'], 'edit' )

		eventtesting.clearEvents()

		res = testapp.delete( entry_url )
		assert_that( res.status_int, is_( 204 ) )


		res = testapp.get( '/dataserver2/users/sjohnson@nextthought.com/Blog' )
		assert_that( res.json_body, has_entry( 'TopicCount', 0 ) )
		testapp.get( entry_url, status=404 )
		testapp.get( story_url, status=404 )

		# When the container was deleted, it fired an ObjectRemovedEvent.
		# This was dispatched to sublocations and refired, resulting
		# in intids being removed for all children
		del_events = eventtesting.getEvents( lifecycleevent.IObjectRemovedEvent )
		assert_that( del_events, has_length( 1 ) )


		assert_that( eventtesting.getEvents( IIntIdRemovedEvent ), has_length( 2 ) )

	@WithSharedApplicationMockDS(users=True,testapp=True)
	def test_user_can_POST_new_comment_PUT_to_edit_and_DELETE( self ):
		"""POSTing an IPost to the URL of an existing IStoryTopic adds a comment"""

		testapp = self.testapp

		data = { 'Class': 'Post',
				 'title': 'My New Blog',
				 'body': ['My first thought'] }

		# Create the blog
		res = testapp.post_json( '/dataserver2/users/sjohnson@nextthought.com/Blog', data )
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


		post_url = self.require_link_href_with_rel( res.json_body, 'edit' )
		self.require_link_href_with_rel( res.json_body, 'like' ) # comments can be liked
		self.require_link_href_with_rel( res.json_body, 'flag' ) # comments can be flagged
		data['body'] = ['Changed my body']
		data['title'] = 'Changed my title'

		res = testapp.put_json( post_url, data )
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

		# until we delete it
		eventtesting.clearEvents()
		res = testapp.delete( post_url )
		assert_that( res.status_int, is_( 204 ) )

		# When it is replaced with placeholders
		res = testapp.get( entry_url )
		assert_that( res.json_body, has_entry( 'PostCount', 1 ) )
		# and nothing was actually deleted yet
		del_events = eventtesting.getEvents( lifecycleevent.IObjectRemovedEvent )
		assert_that( del_events, has_length( 0 ) )
		assert_that( eventtesting.getEvents( IIntIdRemovedEvent ), has_length( 0 ) )

	@WithSharedApplicationMockDS
	def test_user_sharing_community_can_GET_and_POST_new_comments(self):
		with mock_dataserver.mock_db_trans(self.ds):
			user = self._create_user( username='original_user@foo' )
			user2 = self._create_user( username=user.username + '2' )
			# make them share a community
			community = users.Community.create_community( username='TheCommunity' )
			user.join_community( community )
			user2.join_community( community )
			user2_username = user2.username
			user_username = user.username


		testapp = TestApp( self.app, extra_environ=self._make_extra_environ(username=user_username) )
		testapp2 = TestApp( self.app, extra_environ=self._make_extra_environ(username=user2_username) )

		# First user creates the blog entry
		data = { 'Class': 'Post',
				 'title': 'My New Blog',
				 'body': ['My first thought'] }

		# Create the blog
		res = testapp.post_json( '/dataserver2/users/original_user@foo/Blog', data )
		entry_url = res.location
		entry_contents_url = self.require_link_href_with_rel( res.json_body, 'contents' )
		story_url = self.require_link_href_with_rel( res.json_body['headline'], 'edit' )
		pub_url = self.require_link_href_with_rel( res.json_body, 'publish' )

		# Before its published, the second user can see nothing
		res = testapp2.get( '/dataserver2/users/original_user@foo/Blog/contents' )
		assert_that( res.json_body['Items'], has_length( 0 ) )

		# XXX FIXME: This is wrong; TopicCount should be of the visible, not the total, contents
		res = testapp2.get( '/dataserver2/users/original_user@foo/Blog' )
		assert_that( res.json_body, has_entry( 'TopicCount', 1 ) )

		# When it is published...
		testapp.post( pub_url )

		# Second user is able to see everything about it...
		def assert_shared_with_community( data ):
			assert_that( data,  has_entry( 'sharedWith', contains( 'TheCommunity' ) ) )

		# Its entry in the table-of-contents
		res = testapp2.get( '/dataserver2/users/original_user@foo/Blog' )
		assert_that( res.json_body, has_entry( 'TopicCount', 1 ) )

		# Its full entry
		res = testapp2.get( '/dataserver2/users/original_user@foo/Blog/contents' )
		assert_that( res.json_body['Items'][0], has_entry( 'title', 'My New Blog' ) )
		assert_that( res.json_body['Items'][0], has_entry( 'headline', has_entry( 'body', data['body'] ) ) )
		assert_shared_with_community( res.json_body['Items'][0] )

		# It can be fetched by pretty URL
		res = testapp2.get( UQ( '/dataserver2/users/original_user@foo/Blog/My New Blog' ) ) # Pretty URL
		assert_that( res, has_property( 'content_type', 'application/vnd.nextthought.forums.personalblogentry+json' ) )
		assert_that( res.json_body, has_entry( 'title', 'My New Blog' ) )
		assert_that( res.json_body, has_entry( 'headline', has_entry( 'body', data['body'] ) ) )
		assert_shared_with_community( res.json_body )

		contents_href = self.require_link_href_with_rel( res.json_body, 'contents' )
		self.require_link_href_with_rel( res.json_body, 'like' ) # entries can be liked
		self.require_link_href_with_rel( res.json_body, 'flag' ) # entries can be flagged

		# It can be fetched directly
		testapp2.get( entry_url )

		# It can be seen in the activity stream
		res = testapp2.get( '/dataserver2/users/original_user@foo/Activity' )
		assert_that( res.json_body['Items'], contains( has_entry( 'title', data['title'] ) ) )

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
		comment2res = testapp2.post_json( UQ( '/dataserver2/users/original_user@foo/Blog/My New Blog' ), data )
		# (Note that although we're just sending in Posts, the location transforms them:
		assert_that( comment1res, has_property( 'content_type', 'application/vnd.nextthought.forums.personalblogcomment+json' ) )
		assert_that( comment1res.json_body, has_entry( 'MimeType', 'application/vnd.nextthought.forums.personalblogcomment' ) )
		# )

		# These created notifications to the author
		events = eventtesting.getEvents( chat_interfaces.IUserNotificationEvent )
		assert_that( events, has_length( 2 ) )
		for evt in events:
			assert_that( evt.targets, is_( (user_username,) ) )
			assert_that( evt.args[0], has_property( 'type', nti_interfaces.SC_CREATED ) )

		# Both of these the other user can update
		data['title'] = 'Changed my title'
		testapp2.put_json( self.require_link_href_with_rel( comment2res.json_body, 'edit' ), data )

		# (Though he cannot update the actual post itself)
		testapp2.put_json( story_url, data, status=403 )

		# Both visible to the original user
		res = testapp.get( entry_url )
		unpub_url = self.require_link_href_with_rel( res.json_body, 'unpublish' )
		# ... metadata
		assert_that( res.json_body, has_entry( 'PostCount', 2 ) )

		# ... actual contents
		res = testapp.get( entry_contents_url )
		assert_that( res.json_body['Items'], has_length( 2 ) )
		assert_that( res.json_body['Items'], contains_inanyorder(
												has_entry( 'title', data['title'] ),
												has_entry( 'title', 'A comment' ) ) )
		for item in res.json_body['Items']:
			# sharedWith value trickles down to the comments automatically
			assert_shared_with_community( item )

		# ... in the blog feed for both users...
		for app in testapp, testapp2:
			res = app.get( UQ( '/dataserver2/users/original_user@foo/Blog/My New Blog/feed.atom' ) )
			assert_that( res.content_type, is_( 'application/atom+xml'))
			res._use_unicode = False
			pq = PyQuery( res.body, parser='html', namespaces={u'atom': u'http://www.w3.org/2005/Atom'} ) # html to ignore namespaces. Sigh.

			titles = sorted( [x.text for x in pq( b'entry title' )] )
			sums = sorted( [x.text for x in pq( b'entry summary')] )
			assert_that( titles, contains( 'A comment', 'Changed my title' ) )
			assert_that( sums, contains( 'A comment body', 'more comment body') )


		# The original user can unpublish...
		res = testapp.post( unpub_url )
		assert_that( res.json_body, has_entry( 'sharedWith', is_empty() ) )
		# ... making it invisible to the other user
		res = testapp2.get( '/dataserver2/users/original_user@foo/Blog/contents' )
		assert_that( res.json_body['Items'], has_length( 0 ) )
		testapp2.get( entry_url, status=403 )

		# and it can be republished...
		res = testapp.post( pub_url )
		assert_shared_with_community( res.json_body )
		# ...and made visible again
		res = testapp2.get( '/dataserver2/users/original_user@foo/Blog/contents' )
		assert_that( res.json_body['Items'][0], has_entry( 'title', 'My New Blog' ) )



		# The original user can delete a comment from the other user
		testapp.delete( self.require_link_href_with_rel( comment1res.json_body, 'edit' ), status=204 )

		# and the other user can delete his own comment
		testapp2.delete( self.require_link_href_with_rel( comment2res.json_body, 'edit' ), status=204 )

		# and they are now gone

		# replaced by placeholders in the contents
		res = testapp.get( entry_contents_url )
		assert_that( res.json_body['Items'], has_length( 2 ) )
		assert_that( res.json_body['Items'], contains_inanyorder(
												has_entries( 'Deleted', True,  'title', 'This object has been deleted.' ),
												has_entries( 'Deleted', True,  'title', 'This object has been deleted.' ) ) )

		# and in the metadata
		res = testapp.get( entry_url )
		assert_that( res.json_body, has_entry( 'PostCount', 2 ) )

		# Even though they still exist at the same place, they cannot be used in any way
		testapp2.delete( self.require_link_href_with_rel( comment2res.json_body, 'edit' ), status=404 )
		testapp2.get( self.require_link_href_with_rel( comment2res.json_body, 'edit' ), status=404 )
		testapp2.put_json( self.require_link_href_with_rel( comment2res.json_body, 'edit' ), data, status=404 )
