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
from hamcrest import contains
from hamcrest import contains_inanyorder
from hamcrest import has_length
from hamcrest import has_entry

from .test_application import TestApp

from zope import lifecycleevent
from zope.component import eventtesting
from zope.intid.interfaces import IIntIdRemovedEvent

from nti.dataserver import users
from nti.dataserver.tests import mock_dataserver

from .test_application import SharedApplicationTestBase, WithSharedApplicationMockDS, PersistentContainedExternal

from urllib import quote as UQ

class TestApplicationBlogging(SharedApplicationTestBase):

	@WithSharedApplicationMockDS(users=True,testapp=True)
	def test_user_has_default_blog( self ):
		testapp = self.testapp
		res = testapp.get( '/dataserver2/users/sjohnson@nextthought.com/Blog' )

		assert_that( res, has_property( 'content_type', 'application/vnd.nextthought.forums.personalblog+json' ) )
		assert_that( res.json_body, has_entry( 'title', 'sjohnson@nextthought.com' ) )

		# We have a contents URL
		contents_href = self.require_link_href_with_rel( res.json_body, 'contents' )
		# Make sure we're getting back pretty URLs
		assert_that( contents_href, is_( UQ( '/dataserver2/users/sjohnson@nextthought.com/Blog/contents' ) ))
		# which is empty
		testapp.get( contents_href, status=200 )

	@WithSharedApplicationMockDS(users=True,testapp=True)
	def test_user_can_POST_new_blog_entry( self ):
		"""POSTing an IPost to the blog URL automatically creates a new topic"""

		testapp = self.testapp

		data = { 'Class': 'Post',
				 'title': 'My New Blog',
				 'body': ['My first thought'] }

		res = testapp.post_json( '/dataserver2/users/sjohnson@nextthought.com/Blog', data )

		# Return the representation of the new topic created
		assert_that( res, has_property( 'content_type', 'application/vnd.nextthought.forums.personalblogentry+json' ) )
		assert_that( res.json_body, has_entry( 'title', 'My New Blog' ) )
		assert_that( res.json_body, has_entry( 'story', has_entry( 'body', data['body'] ) ) )
		assert_that( res.status_int, is_( 201 ) )
		contents_href = self.require_link_href_with_rel( res.json_body, 'contents' )
		self.require_link_href_with_rel( res.json_body, 'like' ) # entries can be liked
		self.require_link_href_with_rel( res.json_body, 'flag' ) # entries can be flagged

		# The new topic is accessible at its OID URL, plus a pretty URL

		testapp.get( res.location ) # OID URL

		testapp.get( UQ( '/dataserver2/users/sjohnson@nextthought.com/Blog/My New Blog' ) ) # Pretty URL

		# and it has no contents
		testapp.get( contents_href, status=200 )

		# It shows up in the blog contents

		res = testapp.get( '/dataserver2/users/sjohnson@nextthought.com/Blog/contents' )
		assert_that( res.json_body['Items'], contains( has_entry( 'title', data['title'] ) ) )


	@WithSharedApplicationMockDS(users=True,testapp=True)
	def test_user_can_PUT_to_edit_existing_blog_entry( self ):
		"""PUTting an IPost to the 'story' of a blog entry edits the story"""

		testapp = self.testapp

		data = { 'Class': 'Post',
				 'title': 'My New Blog',
				 'body': ['My first thought'] }

		res = testapp.post_json( '/dataserver2/users/sjohnson@nextthought.com/Blog', data )
		entry_url = res.location
		# I can PUT directly to the object URL
		story_url = self.require_link_href_with_rel( res.json_body['story'], 'edit' )

		data['body'] = ['An updated body']

		testapp.put_json( story_url, data )

		# And check it by getting the whole container
		res = testapp.get( entry_url )
		assert_that( res.json_body, has_entry( 'story', has_entry( 'body', data['body'] ) ) )

		# Changing the title changes the title of the container, but NOT the url or ID of anything
		data['title'] = 'A New Title'
		testapp.put_json( story_url, data )
		res = testapp.get( entry_url )
		assert_that( res.json_body, has_entry( 'story', has_entry( 'title', data['title'] ) ) )
		assert_that( res.json_body, has_entry( 'title', data['title'] ) )

		# Pretty URL did not change
		testapp.get( UQ( '/dataserver2/users/sjohnson@nextthought.com/Blog/My New Blog' ) )

		# I can also PUT to the pretty path to the object
		data['body'] = ['An even newer body']

		testapp.put_json( UQ( '/dataserver2/users/sjohnson@nextthought.com/Blog/My New Blog/story' ), data )
		res = testapp.get( entry_url )
		assert_that( res.json_body, has_entry( 'story', has_entry( 'body', data['body'] ) ) )

		# And I can use the 'fields' URL to edit just parts of it, including title and body
		for field in 'body', 'title':
			data[field] = 'Edited with fields'
			if field == 'body': data[field] = [data[field]]

			testapp.put_json( story_url + '/++fields++' + field, data[field] )
			res = testapp.get( entry_url )
			assert_that( res.json_body, has_entry( 'story', has_entry( field, data[field] ) ) )



	@WithSharedApplicationMockDS(users=True,testapp=True)
	def test_user_can_DELETE_existing_blog_entry( self ):
		"""A StoryTopic can be deleted from its object URL"""

		testapp = self.testapp

		data = { 'Class': 'Post',
				 'title': 'My New Blog',
				 'body': ['My first thought'] }

		res = testapp.post_json( '/dataserver2/users/sjohnson@nextthought.com/Blog', data )
		entry_url = res.location
		story_url = self.require_link_href_with_rel( res.json_body['story'], 'edit' )

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

		# (Same user) comments on blog by POSTing a new post
		data['title'] = 'A comment'
		data['body'] = ['This is a comment body']

		res = testapp.post_json( entry_url, data )

		assert_that( res.status_int, is_( 201 ) )
		assert_that( res.json_body, has_entry( 'title', data['title'] ) )
		assert_that( res.json_body, has_entry( 'body', data['body'] ) )
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

		res = testapp.get( entry_url )
		assert_that( res.json_body, has_entry( 'PostCount', 0 ) )

		del_events = eventtesting.getEvents( lifecycleevent.IObjectRemovedEvent )
		assert_that( del_events, has_length( 1 ) )
		assert_that( eventtesting.getEvents( IIntIdRemovedEvent ), has_length( 1 ) )

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
		story_url = self.require_link_href_with_rel( res.json_body['story'], 'edit' )
		pub_url = self.require_link_href_with_rel( res.json_body, 'publish' )

		# Before its published, the second user can see nothing
		res = testapp2.get( '/dataserver2/users/original_user@foo/Blog/contents' )
		assert_that( res.json_body['Items'], has_length( 0 ) )

		# XXX FIXME: This is wrong
		res = testapp2.get( '/dataserver2/users/original_user@foo/Blog' )
		assert_that( res.json_body, has_entry( 'TopicCount', 1 ) )

		# When it is published...
		testapp.post( pub_url )

		# Second user is able to see everything about it...

		# Its entry in the table-of-contents
		res = testapp2.get( '/dataserver2/users/original_user@foo/Blog' )
		assert_that( res.json_body, has_entry( 'TopicCount', 1 ) )

		# Its full entry
		res = testapp2.get( '/dataserver2/users/original_user@foo/Blog/contents' )
		assert_that( res.json_body['Items'][0], has_entry( 'title', 'My New Blog' ) )
		assert_that( res.json_body['Items'][0], has_entry( 'story', has_entry( 'body', data['body'] ) ) )

		# It can be fetched by pretty URL
		res = testapp2.get( UQ( '/dataserver2/users/original_user@foo/Blog/My New Blog' ) ) # Pretty URL
		assert_that( res, has_property( 'content_type', 'application/vnd.nextthought.forums.personalblogentry+json' ) )
		assert_that( res.json_body, has_entry( 'title', 'My New Blog' ) )
		assert_that( res.json_body, has_entry( 'story', has_entry( 'body', data['body'] ) ) )
		contents_href = self.require_link_href_with_rel( res.json_body, 'contents' )
		self.require_link_href_with_rel( res.json_body, 'like' ) # entries can be liked
		self.require_link_href_with_rel( res.json_body, 'flag' ) # entries can be flagged

		# It can be fetched directly
		testapp2.get( entry_url )

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

		# Which he can update
		data['title'] = 'Changed my title'
		testapp2.put_json( self.require_link_href_with_rel( comment2res.json_body, 'edit' ), data )

		# (Though he cannot update the actual post itself)
		testapp2.put_json( story_url, data, status=403 )

		# Both visible to the original user
		res = testapp.get( entry_url )
		# ... metadata
		assert_that( res.json_body, has_entry( 'PostCount', 2 ) )

		# ... actual contents
		res = testapp.get( entry_contents_url )
		assert_that( res.json_body['Items'], has_length( 2 ) )
		assert_that( res.json_body['Items'], contains_inanyorder(
			has_entry( 'title', data['title'] ),
			has_entry( 'title', 'A comment' ) ) )

		# The original user can delete a comment from the other user
		testapp.delete( self.require_link_href_with_rel( comment1res.json_body, 'edit' ), status=204 )

		# and the other user can delete his own comment
		testapp2.delete( self.require_link_href_with_rel( comment2res.json_body, 'edit' ), status=204 )

		# and they are now gone
		res = testapp.get( entry_url )
		# ... metadata
		assert_that( res.json_body, has_entry( 'PostCount', 0 ) )
