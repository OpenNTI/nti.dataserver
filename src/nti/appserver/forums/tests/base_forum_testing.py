#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A base class for testing forum-based code.

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
from hamcrest import not_none
from hamcrest import has_item
from hamcrest import contains
from hamcrest import contains_inanyorder
from hamcrest import contains_string
from hamcrest import has_length
from hamcrest import has_entry
from hamcrest import has_entries
from hamcrest import ends_with
from hamcrest import greater_than
from hamcrest import has_key

from nti.tests import is_empty
from nti.tests import time_monotonically_increases
import fudge

from nti.appserver.tests.test_application import TestApp as _TestApp
from nti.appserver.tests import test_application_censoring

import datetime
import webob.datetime_utils

from zope import lifecycleevent
from zope import interface
from zope.component import eventtesting
from zope.intid.interfaces import IIntIdRemovedEvent
from zope.location.interfaces import ISublocations

import simplejson as json

from nti.ntiids import ntiids
from nti.dataserver import users
from nti.dataserver import interfaces as nti_interfaces
from nti.dataserver.contenttypes.forums import interfaces as frm_interfaces
from nti.chatserver import interfaces as chat_interfaces
from nti.dataserver.tests import mock_dataserver

from nti.dataserver.contenttypes.forums.forum import CommunityForum
from nti.dataserver.contenttypes.forums.topic import PersonalBlogEntry


from nti.appserver.tests.test_application import SharedApplicationTestBase, WithSharedApplicationMockDS

from urllib import quote as UQ
from pyquery import PyQuery


# TODO: FIXME: This solves an order-of-imports issue, where
# mimeType fields are only added to the classes when externalization is
# loaded (usually with ZCML, so in practice this is not a problem,
# but statically and in isolated unit-tests, it could be)
from nti.dataserver.contenttypes.forums import externalization as frm_ext
frm_ext = frm_ext

POST_MIME_TYPE = 'application/vnd.nextthought.forums.post'

def _plain(mt):
	return mt[:-5] if mt.endswith( '+json' ) else mt

class _UserCommunityFixture(object):

	def __init__( self, test ):
		self.ds = test.ds
		self.test = test
		with mock_dataserver.mock_db_trans(self.ds):
			user = self._create_user( username='original_user@foo' )
			user2 = self._create_user( username='user2@foo' )
			user3 = self._create_user( username='user3@foo' )
			user_following_2 = self._create_user( username='user_following_2@foo' )
			user2_following_2 = self._create_user( username='user2_following_2@foo' )

			# make them share a community
			community = users.Community.get_community( 'TheCommunity', self.ds ) or users.Community.create_community( username='TheCommunity' )
			user.join_community( community )
			user2.join_community( community )
			user3.join_community( community )
			user_following_2.join_community( community )
			user2_following_2.join_community( community )

			user2.follow( user )
			user_following_2.follow( user2 )
			user2_following_2.follow( user2 )

			user2_username = user2.username
			user_username = user.username
			user3_username = user3.username
			user2_follower_username = user_following_2.username
			user2_follower2_username = user2_following_2.username


		self.testapp = _TestApp( self.app, extra_environ=self._make_extra_environ(username=user_username) )
		self.testapp2 = _TestApp( self.app, extra_environ=self._make_extra_environ(username=user2_username) )
		self.testapp3 = _TestApp( self.app, extra_environ=self._make_extra_environ(username=user3_username) )
		self.user2_followerapp = _TestApp( self.app, extra_environ=self._make_extra_environ(username=user2_follower_username) )
		self.user2_follower2app = _TestApp( self.app, extra_environ=self._make_extra_environ(username=user2_follower2_username) )

	def __getattr__( self, name ):
		return getattr( self.test, name )

class AbstractTestApplicationForumsBase(SharedApplicationTestBase):
	#: make nosetests only run subclasses of this that set __test__ to True
	__test__ = False

	features = SharedApplicationTestBase.features + ('forums',)
	default_username = 'original_user@foo' # Not an admin user by default 'sjohnson@nextthought.com'
	default_entityname = default_username
	forum_ntiid = 'tag:nextthought.com,2011-10:' + default_username + '-Forum:PersonalBlog-Blog'
	forum_url_relative_to_user = 'Blog'
	forum_content_type = None
	forum_headline_class_type = 'Post'
	forum_headline_content_type = POST_MIME_TYPE
	forum_pretty_url = None
	forum_link_rel = None
	forum_title = default_username
	forum_type = None
	forum_topic_content_type = None
	forum_topic_ntiid_base = 'tag:nextthought.com,2011-10:' + default_username + '-Topic:PersonalBlogEntry-'
	forum_topic_comment_content_type = None

	def setUp(self):
		super(AbstractTestApplicationForumsBase,self).setUp()
		self.forum_pretty_url = UQ('/dataserver2/users/' + self.default_entityname + '/' + self.forum_url_relative_to_user)
		self.forum_ntiid_url = UQ('/dataserver2/NTIIDs/' + self.forum_ntiid)
		self.forum_pretty_contents_url = self.forum_pretty_url + '/contents'
		self.default_username_url = UQ('/dataserver2/users/' + self.default_username )
		self.default_username_pages_url = self.default_username_url + '/Pages'

	def forum_topic_ntiid( self, entryid ):
		return self.forum_topic_ntiid_base + entryid

	def forum_topic_href( self, entryid ):
		return self.forum_pretty_url + '/' + UQ( entryid )

	@WithSharedApplicationMockDS(users=True,testapp=True)
	def test_entity_has_default_forum( self ):
		testapp = self.testapp

		# The forum can be found at a pretty url, and by NTIID
		pretty_url = self.forum_pretty_url
		ntiid_url = self.forum_ntiid_url
		for url in pretty_url, ntiid_url:
			res = testapp.get( url )
			blog_res = res
			assert_that( res, has_property( 'content_type', self.forum_content_type ) )
			assert_that( res.json_body, has_entry( 'title', self.forum_title ) )
			assert_that( res.json_body, has_entry( 'NTIID', self.forum_ntiid ) )

			# We have a contents URL
			contents_href = self.require_link_href_with_rel( res.json_body, 'contents' )
			# Make sure we're getting back pretty URLs...
			assert_that( contents_href, is_( self.forum_pretty_contents_url ) )
			# which is empty...
			testapp.get( contents_href, status=200 )

			# The forum cannot be liked, favorited, flagged
			self.forbid_link_with_rel( blog_res.json_body, 'like' )
			self.forbid_link_with_rel( blog_res.json_body, 'flag' )
			self.forbid_link_with_rel( blog_res.json_body, 'favorite' )

	@WithSharedApplicationMockDS(users=True,testapp=True)
	def test_user_cannot_POST_new_forum_entry_to_pages( self ):
		testapp = self.testapp

		data = self._create_post_data_for_POST()

		# No containerId
		testapp.post_json( self.default_username_url, data, status=422 )
		testapp.post_json( self.default_username_pages_url, data, status=422 )

		data['ContainerId'] = 'tag:foo:bar'
		testapp.post_json( self.default_username_url, data, status=422 )
		res = testapp.post_json( self.default_username_pages_url, data, status=422 )

		assert_that( res.json_body, has_entry( 'code', 'InvalidContainerType' ) )
		assert_that( res.json_body, has_entry( 'field', 'ContainerId' ) )
		assert_that( res.json_body, has_entry( 'message', is_not( is_empty() ) ) )

	@WithSharedApplicationMockDS(users=True,testapp=True)
	def test_user_can_POST_new_forum_entry_and_flagging_returns_same_href( self ):
		data = self._create_post_data_for_POST()

		res = self._POST_topic_entry( data, status_only=201 )

		assert_that( res.location, is_( 'http://localhost' + res.json_body['href'] + '/' ) )
		self.testapp.get( res.location ) # ensure it can be fetched from here

		topic_res = self.testapp.get( res.json_body['href'] ) # as well as its internal href
		assert_that( topic_res.json_body, has_entry( 'title', data['title'] ) )
		assert_that( topic_res.json_body, has_entry( 'MimeType', _plain(self.forum_topic_content_type) ) )
		topic_href = res.json_body['href']

		flag_href = self.require_link_href_with_rel( res.json_body, 'flag' )
		res2 = self.testapp.post( flag_href )

		assert_that( res2.json_body['href'], is_( topic_href ) )
		self.require_link_href_with_rel( res2.json_body, 'flag.metoo' )
		self.forbid_link_with_rel( res2.json_body, 'flag' )

	@WithSharedApplicationMockDS(users=True,testapp=True)
	def test_user_can_POST_new_forum_entry_header_only( self ):
		data = self._create_post_data_for_POST()

		# With neither, but a content-type header
		del data['MimeType']
		del data['Class']

		self._do_test_user_can_POST_new_forum_entry( data, content_type=POST_MIME_TYPE )

	@WithSharedApplicationMockDS(users=True,testapp=True)
	def test_user_can_POST_new_forum_entry_class_only( self ):
		data = self._create_post_data_for_POST()
		del data['MimeType']

		self._do_test_user_can_POST_new_forum_entry( data )


	@WithSharedApplicationMockDS(users=True,testapp=True)
	def test_user_can_POST_new_forum_entry_mime_type_only( self ):
		data = self._create_post_data_for_POST()
		del data['Class']

		self._do_test_user_can_POST_new_forum_entry( data )

	@WithSharedApplicationMockDS(users=True,testapp=True)
	def test_user_can_POST_new_forum_entry_uncensored_by_default( self ):
		data = self._create_post_data_for_POST()
		data['title'] = test_application_censoring.bad_word
		data['body'] = [test_application_censoring.bad_val]

		self._do_test_user_can_POST_new_forum_entry( data )

	@WithSharedApplicationMockDS(users=True,testapp=True)
	def test_user_can_POST_new_forum_entry_resulting_in_blog_being_sublocation( self ):
		# Creating a Blog causes it to be a sublocation of the entity
		# This way deleting/moving the user correctly causes the blog to be deleted/moved

		self._POST_topic_entry( self._create_post_data_for_POST() )

		with mock_dataserver.mock_db_trans( self.ds ):
			entity = users.Entity.get_entity( self.default_entityname )

			all_subs = set()
			def _recur( i ):
				all_subs.add( i )
				subs = ISublocations( i, None )
				if subs:
					for x in subs.sublocations():
						_recur( x )
			_recur( entity )

			assert_that( all_subs, has_item( is_( self.forum_type ) ) )

	@WithSharedApplicationMockDS(users=True,testapp=True)
	def test_user_can_PUT_to_edit_existing_forum_topic_headline( self ):

		testapp = self.testapp

		data = self._create_post_data_for_POST()
		res = self._POST_topic_entry( data )

		topic_url = res.location
		assert_that( topic_url, contains_string( self.forum_pretty_url ) )
		# I can PUT directly to the headline's edit URL
		headline_url = self.require_link_href_with_rel( res.json_body['headline'], 'edit' )
		# Which is not 'pretty'
		assert_that( headline_url, contains_string( 'Objects' ) )

		data['body'] = ['An updated body']
		testapp.put_json( headline_url, data )

		# And check it by getting the whole container
		res = testapp.get( topic_url )
		assert_that( res.json_body, has_entry( 'headline', has_entry( 'body', data['body'] ) ) )

		# Changing the title changes the title of the container, but NOT the url or ID of anything
		data['title'] = 'A New Title'
		testapp.put_json( headline_url, data )
		res = testapp.get( topic_url )
		assert_that( res.json_body, has_entry( 'headline', has_entry( 'title', data['title'] ) ) )
		assert_that( res.json_body, has_entry( 'title', data['title'] ) )

		# Pretty URL did not change
		testapp.get( topic_url )

		# I can also PUT to the pretty path to the headline
		data['body'] = ['An even newer body']

		testapp.put_json( topic_url + 'headline', data )
		res = testapp.get( topic_url )
		assert_that( res.json_body, has_entry( 'headline', has_entry( 'body', data['body'] ) ) )

		# And I can use the 'fields' URL to edit just parts of it, including title and body
		for field in 'body', 'title':
			data[field] = 'Edited with fields'
			if field == 'body': data[field] = [data[field]]

			testapp.put_json( headline_url + '/++fields++' + field, data[field] )
			res = testapp.get( topic_url )
			assert_that( res.json_body, has_entry( 'headline', has_entry( field, data[field] ) ) )

	@WithSharedApplicationMockDS(users=True,testapp=True)
	@time_monotonically_increases
	def test_user_can_POST_new_comment( self ):
		#"""POSTing an IPost to the URL of an existing IStoryTopic adds a comment"""

		testapp = self.testapp

		# Create the topic
		res = self._POST_topic_entry()
		entry_url = res.location
		entry_ntiid = res.json_body['NTIID']


		# (Same user) comments on blog by POSTing a new post
		data = self._create_comment_data_for_POST()

		res = testapp.post_json( entry_url, data, status=201 )

		assert_that( res.status_int, is_( 201 ) )
		assert_that( res.json_body, has_entry( 'title', data['title'] ) )
		assert_that( res.json_body, has_entry( 'body', data['body'] ) )
		assert_that( res.json_body, has_entry( 'ContainerId', entry_ntiid) )
		assert_that( res, has_property( 'content_type', self.forum_topic_comment_content_type ) )
		assert_that( res.location, is_( 'http://localhost' + res.json_body['href'] + '/' ) )


		res = testapp.get( entry_url )
		assert_that( res.json_body, has_entry( 'PostCount', 1 ) )


	@WithSharedApplicationMockDS(users=True,testapp=True)
	@time_monotonically_increases
	def test_creator_can_DELETE_comment( self ):
		testapp = self.testapp

		# Create the topic
		res = self._POST_topic_entry()
		entry_url = res.location
		entry_contents_url = self.require_link_href_with_rel( res.json_body, 'contents' )
		#entry_ntiid = res.json_body['NTIID']

		data = self._create_comment_data_for_POST()
		res = testapp.post_json( entry_url, data, status=201 )
		assert_that( res.status_int, is_( 201 ) )
		edit_url = self.require_link_href_with_rel( res.json_body, 'edit' )
		entry_creation_time = res.json_body['Last Modified']

		eventtesting.clearEvents()

		res = testapp.delete( edit_url )
		assert_that( res.status_int, is_( 204 ) )

		# When it is replaced with placeholders
		res = testapp.get( entry_url )
		assert_that( res.json_body, has_entry( 'PostCount', 1 ) )
		# and nothing was actually deleted yet
		del_events = eventtesting.getEvents( lifecycleevent.IObjectRemovedEvent )
		assert_that( del_events, has_length( 0 ) )
		assert_that( eventtesting.getEvents( IIntIdRemovedEvent ), has_length( 0 ) )

		# But modification events did fire...
		mod_events = eventtesting.getEvents( lifecycleevent.IObjectModifiedEvent )
		assert_that( mod_events, has_length( 1 ) )
		# ...resulting in an updated time for the contents view
		res = testapp.get( entry_contents_url )
		assert_that( res.json_body['Last Modified'], is_( greater_than( entry_creation_time ) ) )


	@WithSharedApplicationMockDS(users=True,testapp=True)
	def test_creator_can_DELETE_existing_empty_forum_topic( self ):
		testapp = self.testapp

		res = self._POST_topic_entry()
		topic_url = res.location
		headline_url = self.require_link_href_with_rel( res.json_body['headline'], 'edit' )

		eventtesting.clearEvents()

		res = testapp.delete( topic_url )
		assert_that( res.status_int, is_( 204 ) )

		res = testapp.get( self.forum_pretty_url )
		assert_that( res.json_body, has_entry( 'TopicCount', 0 ) )
		testapp.get( topic_url, status=404 )
		testapp.get( headline_url, status=404 )

		# When the topic was deleted from the forum, it fired a single ObjectRemovedEvent.
		# This was dispatched to sublocations and refired, resulting
		# in intids being removed for the topic and the headline.
		# (TODO: This isn't symmetrical with ObjectAddedEvent; we get one for topic and headline,
		# right?)
		assert_that( eventtesting.getEvents( lifecycleevent.IObjectRemovedEvent ), has_length( 1 ) )
		assert_that( eventtesting.getEvents( IIntIdRemovedEvent ), has_length( 2 ) )

	@WithSharedApplicationMockDS(users=True,testapp=True)
	def test_creator_cannot_change_sharing_on_topic_or_any_child( self ):
		#""" Sharing is fixed and cannot be changed for a blog entry, its story, or a comment"""

		testapp = self.testapp
		res = self._POST_topic_entry()

		topic_url = res.location
		headline_url = self.require_link_href_with_rel( res.json_body['headline'], 'edit' )

		eventtesting.clearEvents()

		# Field updates
		# Cannot change the entry
		testapp.put_json( topic_url + '/++fields++sharedWith',
						  ['Everyone'],
						  # Because of the way traversal is right now, this results in a 404,
						  # when really we want a 403
						  status=404)

		# Cannot change the story
		testapp.put_json( headline_url + '/++fields++sharedWith',
						  ['Everyone'],
						  status=404) # same as above


		# Nor when putting the whole thing
		# The entry itself simply cannot be modified (predicate mismatch right now)
		testapp.put_json( topic_url,
						  {'sharedWith': ['Everyone']},
						  status=404 )

		# The story accepts it but ignores it
		res = testapp.put_json( headline_url,
								{'sharedWith': ['Everyone']},
								status=200 )
		assert_that( res.json_body, has_entry( 'sharedWith', is_empty() ) )

		res = testapp.get( headline_url )
		assert_that( res.json_body, has_entry( 'sharedWith', is_empty() ) )

	@WithSharedApplicationMockDS
	@time_monotonically_increases
	def test_creator_can_publish_topic_simple_visible_to_other_user_in_community(self):
		fixture = _UserCommunityFixture( self )
		self.testapp = testapp = fixture.testapp
		testapp2 = fixture.testapp2

		# First user creates the topic
		data = self._create_post_data_for_POST()
		topic_data = data.copy()

		# Create the blog
		res = self._POST_topic_entry( topic_data )
		topic_url = res.location
		#topic_ntiid = res.json_body['NTIID']
		topic_entry_id = res.json_body['ID']
		self.require_link_href_with_rel( res.json_body, 'contents' )
		self.require_link_href_with_rel( res.json_body['headline'], 'edit' )

		publish_url = self.require_link_href_with_rel( res.json_body, 'publish' )


		# Before its published, the second user can see nothing
		res = testapp2.get( self.forum_pretty_contents_url )
		assert_that( res.json_body['Items'], has_length( 0 ) )
		content_last_mod = res.json_body['Last Modified']
		assert_that( res.last_modified, is_( datetime.datetime.fromtimestamp( content_last_mod, webob.datetime_utils.UTC ) ) )

		# However, he can detect that there is a post
		# XXX FIXME: This is wrong; TopicCount should be of the visible, not the total, contents
		res = testapp2.get( self.forum_pretty_url )
		assert_that( res.json_body, has_entry( 'TopicCount', 1 ) )

		# When it is published...
		testapp.post( publish_url )

		# Second user is able to see everything about it...
		def assert_shared_with_community( data ):
			assert_that( data,  has_entry( 'sharedWith', contains( 'TheCommunity' ) ) )

		# ...Its entry in the table-of-contents...
		res = testapp2.get( self.forum_pretty_url )
		assert_that( res.json_body, has_entry( 'TopicCount', 1 ) )

		# ...Its full entry...
		res = testapp2.get( self.forum_pretty_contents_url )
		__traceback_info__ = self.forum_pretty_contents_url
		assert_that( res.json_body['Items'][0], has_entry( 'title', topic_data['title'] ) )
		assert_that( res.json_body['Items'][0], has_entry( 'headline', has_entry( 'body', topic_data['body'] ) ) )
		assert_shared_with_community( res.json_body['Items'][0] )
		# ...Which has an updated last modified...
		assert_that( res.json_body['Last Modified'], greater_than( content_last_mod ) )
		content_last_mod = res.json_body['Last Modified']
		assert_that( res.last_modified, is_( datetime.datetime.fromtimestamp( content_last_mod, webob.datetime_utils.UTC ) ) )

		# ...It can be fetched by pretty URL...
		res = testapp2.get( self.forum_topic_href( topic_entry_id ) )
		assert_that( res, has_property( 'content_type', self.forum_topic_content_type ) )
		assert_that( res.json_body, has_entry( 'title', topic_data['title'] ) )
		assert_that( res.json_body, has_entry( 'ID', topic_entry_id ) )
		assert_that( res.json_body, has_entry( 'headline', has_entry( 'body', topic_data['body'] ) ) )
		assert_shared_with_community( res.json_body )

		#XXX contents_href = self.require_link_href_with_rel( res.json_body, 'contents' )
		#XXX self.require_link_href_with_rel( res.json_body, 'like' ) # entries can be liked
		self.require_link_href_with_rel( res.json_body, 'flag' ) # entries can be flagged

		# ...It can be fetched directly...
		testapp2.get( topic_url )

	@WithSharedApplicationMockDS
	@time_monotonically_increases
	def test_published_topic_is_in_activity(self):
		fixture = _UserCommunityFixture( self )
		self.testapp = testapp = fixture.testapp
		testapp2 = fixture.testapp2

		_, data = self._POST_and_publish_topic_entry()

		# ...It can be seen in the activity stream for the author by the author and the people it
		# is shared with ...
		for app in testapp, testapp2:
			res = self.fetch_user_activity( app, self.default_username )
			__traceback_info__ = res.json_body
			assert_that( res.json_body['Items'], contains( has_entry( 'title', data['title'] ) ) )

	def _create_post_data_for_POST(self):
		data = { 'Class': self.forum_headline_class_type,
				 'MimeType': self.forum_headline_content_type,
				 'title': 'My New Blog',
				 'body': ['My first thought'] }
		return data

	def _create_comment_data_for_POST(self):
		data = { 'Class': 'Post',
				 'title': 'A comment',
				 'body': ['This is a comment body'] }
		return data

	def _POST_topic_entry( self, data=None, content_type=None, status_only=None ):
		testapp = self.testapp
		if data is None:
			data = self._create_post_data_for_POST()

		kwargs = {'status': 201}
		meth = testapp.post_json
		post_data = data
		if content_type:
			kwargs['headers'] = {b'Content-Type': str(content_type)}
			# testapp.post_json forces the content-type header
			meth = testapp.post
			post_data = json.dumps( data )
		if status_only:
			kwargs['status'] = status_only

		res = meth(  self.forum_pretty_url,
					 post_data,
					 **kwargs )

		return res

	def _POST_and_publish_topic_entry( self, data=None ):
		""" Returns (publish Response, topic data) """
		if data is None:
			data = self._create_post_data_for_POST()
		res = self._POST_topic_entry( data=data )

		publish_url = self.require_link_href_with_rel( res.json_body, 'publish' )
		res = self.testapp.post( publish_url )
		return res, data

	def _do_simple_tests_for_POST_of_topic_entry( self, data, content_type=None, status_only=None, expected_data=None ):
		res = self._POST_topic_entry( data, content_type=content_type, status_only=status_only )
		if status_only:
			return res

		# Returns the representation of the new topic created
		data = expected_data or data
		assert_that( res, has_property( 'content_type', self.forum_topic_content_type ) )
		assert_that( res.json_body, has_entry( 'ID', ntiids.make_specific_safe( data['title'] ) ) )
		entry_id = res.json_body['ID']
		assert_that( res.json_body, has_entries( 'title', data['title'],
												 'NTIID', self.forum_topic_ntiid( entry_id ),
												 'ContainerId', self.forum_ntiid,
												 'href', self.forum_topic_href( entry_id ) ) )

		assert_that( res.json_body['headline'], has_entries( 'title', data['title'],
															 'body',  data['body'] ) )

		#contents_href = self.require_link_href_with_rel( res.json_body, 'contents' )
		#self.require_link_href_with_rel( res.json_body, 'like' ) # entries can be liked
		self.require_link_href_with_rel( res.json_body, 'flag' ) # entries can be flagged
		self.require_link_href_with_rel( res.json_body, 'edit' ) # entries can be 'edited' (actually they cannot, shortcut for ui)
		#fav_href = self.require_link_href_with_rel( res.json_body, 'favorite' ) # entries can be favorited

		# The headline cannot be any of those things
		headline_json = res.json_body['headline']
		self.forbid_link_with_rel( headline_json, 'like' )
		self.forbid_link_with_rel( headline_json, 'flag' )
		self.forbid_link_with_rel( headline_json, 'favorite' )

		return res

	_do_test_user_can_POST_new_forum_entry = _do_simple_tests_for_POST_of_topic_entry
