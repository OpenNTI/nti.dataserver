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

from nti.dataserver.contenttypes.forums.forum import PersonalBlog, CommunityForum
from nti.dataserver.contenttypes.forums.topic import PersonalBlogEntry, CommunityHeadlineTopic


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


class _AbstractTestApplicationForums(SharedApplicationTestBase):

	features = SharedApplicationTestBase.features + ('forums',)
	default_username = 'sjohnson@nextthought.com'
	default_entityname = default_username
	forum_ntiid = 'tag:nextthought.com,2011-10:sjohnson@nextthought.com-Forum:PersonalBlog-Blog'
	forum_url_relative_to_user = 'Blog'
	forum_content_type = None
	forum_headline_class_type = 'Post'
	forum_headline_content_type = POST_MIME_TYPE
	forum_pretty_url = None
	forum_link_rel = None
	forum_title = default_username
	forum_type = None
	forum_topic_content_type = None
	forum_topic_ntiid_base = 'tag:nextthought.com,2011-10:sjohnson@nextthought.com-Topic:PersonalBlogEntry-'
	forum_topic_comment_content_type = None

	def setUp(self):
		super(_AbstractTestApplicationForums,self).setUp()
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

class TestApplicationBlogging(_AbstractTestApplicationForums):

	extra_environ_default_user = _AbstractTestApplicationForums.default_username
	forum_link_rel = 'Blog'
	forum_content_type = 'application/vnd.nextthought.forums.personalblog+json'
	forum_headline_class_type = 'Post'
	forum_topic_content_type = PersonalBlogEntry.mimeType + '+json'
	forum_topic_ntiid_base = 'tag:nextthought.com,2011-10:sjohnson@nextthought.com-Topic:PersonalBlogEntry-'
	forum_type = PersonalBlog
	forum_topic_comment_content_type = 'application/vnd.nextthought.forums.personalblogcomment+json'

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
	def test_users_default_blog_not_in_links( self ):
		# Default blog is empty, not in my links
		user = self.resolve_user()
		self.forbid_link_with_rel( user, self.forum_link_rel )

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

		res = self._do_simple_tests_for_POST_of_topic_entry( data, content_type=content_type, status_only=status_only, expected_data=expected_data )
		if status_only:
			return res

		testapp = self.testapp
		data = expected_data or data
		entry_id = res.json_body['ID']

		contents_href = self.require_link_href_with_rel( res.json_body, 'contents' )
		self.require_link_href_with_rel( res.json_body, 'like' ) # entries can be liked
		self.require_link_href_with_rel( res.json_body, 'flag' ) # entries can be flagged
		self.require_link_href_with_rel( res.json_body, 'edit' ) # entries can be 'edited' (actually they cannot, shortcut for ui)
		fav_href = self.require_link_href_with_rel( res.json_body, 'favorite' ) # entries can be favorited

		entry_url = res.location
		entry_ntiid = res.json_body['NTIID']

		# The new topic is accessible at its OID URL, its pretty URL, and by NTIID
		for url in entry_url, UQ( '/dataserver2/users/sjohnson@nextthought.com/Blog/' + entry_id ), UQ( '/dataserver2/NTIIDs/' + entry_ntiid ):
			testapp.get( url )


		# and it has no contents
		testapp.get( contents_href, status=200 )

		# It shows up in the blog contents
		res = testapp.get( '/dataserver2/users/sjohnson@nextthought.com/Blog/contents' )
		blog_items = res.json_body['Items']
		assert_that( blog_items, contains( has_entry( 'title', data['title'] ) ) )
		# With its links all intact
		blog_item = blog_items[0]
		assert_that( blog_item, has_entry( 'href', UQ( '/dataserver2/users/sjohnson@nextthought.com/Blog/' + blog_item['ID'] ) ))
		self.require_link_href_with_rel( blog_item, 'contents' )
		self.require_link_href_with_rel( blog_item, 'like' ) # entries can be liked
		self.require_link_href_with_rel( blog_item, 'flag' ) # entries can be flagged
		self.require_link_href_with_rel( blog_item, 'edit' ) # entries can be 'edited' (actually they cannot)


		# It also shows up in the blog's data feed (partially rendered in HTML)
		res = testapp.get( '/dataserver2/users/sjohnson@nextthought.com/Blog/feed.atom' )
		assert_that( res.content_type, is_( 'application/atom+xml'))
		res._use_unicode = False
		pq = PyQuery( res.body, parser='html', namespaces={u'atom': u'http://www.w3.org/2005/Atom'} ) # html to ignore namespaces. Sigh.
		assert_that( pq( b'entry title' ).text(), is_( data['title'] ) )
		assert_that( pq( b'entry summary' ).text(), is_( '<div><br />' + data['body'][0] ) )


		# And in the user activity view
		res = testapp.get( '/dataserver2/users/sjohnson@nextthought.com/Activity' )
		assert_that( res.json_body['Items'], contains( has_entry( 'title', data['title'] ) ) )
		assert_that( res.json_body['Items'], has_length( 1 ) ) # make sure no dups

		# And in the user root recursive data stream
		res = testapp.get( '/dataserver2/users/sjohnson@nextthought.com/Pages(' + ntiids.ROOT + ')/RecursiveUserGeneratedData' )
		assert_that( res.json_body['Items'], contains( has_entry( 'title', data['title'] ) ) )

		# and, if favorited, filtered to the favorites
		testapp.post( fav_href )
		res = testapp.get( '/dataserver2/users/sjohnson@nextthought.com/Pages(' + ntiids.ROOT + ')/RecursiveUserGeneratedData',
						   params={'filter': 'Favorite'})
		assert_that( res.json_body['Items'], contains( has_entry( 'title', data['title'] ) ) )
		self.require_link_href_with_rel( res.json_body['Items'][0], 'unfavorite' )

		# And in his links
		res = testapp.get( '/dataserver2/ResolveUser/sjohnson@nextthought.com' )
		self.require_link_href_with_rel( res.json_body['Items'][0], 'Blog' )

	_do_test_user_can_POST_new_forum_entry = _do_test_user_can_POST_new_blog_entry


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
	@time_monotonically_increases
	def test_user_can_POST_new_comment_PUT_to_edit_flag_and_DELETE( self ):
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
		assert_that( res.location, is_( 'http://localhost' + res.json_body['href'] + '/' ) )
		post_href = res.json_body['href']

		edit_url = self.require_link_href_with_rel( res.json_body, 'edit' )
		self.require_link_href_with_rel( res.json_body, 'like' ) # comments can be liked
		flag_href = self.require_link_href_with_rel( res.json_body, 'flag' ) # comments can be flagged
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
		contents_mod_time = res.json_body['Last Modified']

		# Can be flagged...
		res = testapp.post( flag_href )
		# ...returning the same href we started with
		assert_that( res.json_body['href'], is_( post_href ) )
		self.require_link_href_with_rel( res.json_body, 'flag.metoo' )

		# until we delete it
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
		assert_that( res.json_body['Last Modified'], is_( greater_than( contents_mod_time ) ) )


	@WithSharedApplicationMockDS
	@time_monotonically_increases
	def test_user_sharing_community_can_GET_and_POST_new_comments(self):
		with mock_dataserver.mock_db_trans(self.ds):
			user = self._create_user( username='original_user@foo' )
			user2 = self._create_user( username='user2@foo' )
			user3 = self._create_user( username='user3@foo' )
			user_following_2 = self._create_user( username='user_following_2@foo' )
			user2_following_2 = self._create_user( username='user2_following_2@foo' )

			# make them share a community
			community = users.Community.create_community( username='TheCommunity' )
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


		testapp = _TestApp( self.app, extra_environ=self._make_extra_environ(username=user_username) )
		testapp2 = _TestApp( self.app, extra_environ=self._make_extra_environ(username=user2_username) )
		testapp3 = _TestApp( self.app, extra_environ=self._make_extra_environ(username=user3_username) )
		user2_followerapp = _TestApp( self.app, extra_environ=self._make_extra_environ(username=user2_follower_username) )
		user2_follower2app = _TestApp( self.app, extra_environ=self._make_extra_environ(username=user2_follower2_username) )

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
		content_last_mod = res.json_body['Last Modified']
		assert_that( res.last_modified, is_( datetime.datetime.fromtimestamp( content_last_mod, webob.datetime_utils.UTC ) ) )

		# XXX FIXME: This is wrong; TopicCount should be of the visible, not the total, contents
		res = testapp2.get( '/dataserver2/users/original_user@foo/Blog' )
		assert_that( res.json_body, has_entry( 'TopicCount', 1 ) )

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
		assert_that( res.json_body['Last Modified'], greater_than( content_last_mod ) )
		content_last_mod = res.json_body['Last Modified']
		assert_that( res.last_modified, is_( datetime.datetime.fromtimestamp( content_last_mod, webob.datetime_utils.UTC ) ) )

		# ...It can be fetched by pretty URL...
		res = testapp2.get( UQ( '/dataserver2/users/original_user@foo/Blog/My_New_Blog' ) ) # Pretty URL
		assert_that( res, has_property( 'content_type', 'application/vnd.nextthought.forums.personalblogentry+json' ) )
		assert_that( res.json_body, has_entry( 'title', 'My New Blog' ) )
		assert_that( res.json_body, has_entry( 'ID', 'My_New_Blog' ) )
		assert_that( res.json_body, has_entry( 'headline', has_entry( 'body', data['body'] ) ) )
		assert_shared_with_community( res.json_body )

		contents_href = self.require_link_href_with_rel( res.json_body, 'contents' )
		self.require_link_href_with_rel( res.json_body, 'like' ) # entries can be liked
		self.require_link_href_with_rel( res.json_body, 'flag' ) # entries can be flagged

		# ...It can be fetched directly...
		testapp2.get( entry_url )

		# ...It can be seen in the activity stream for the author...
		res = testapp2.get( '/dataserver2/users/original_user@foo/Activity' )
		assert_that( res.json_body['Items'], contains( has_entry( 'title', data['title'] ) ) )

		# ...And in the main stream of the follower.
		res = testapp2.get( '/dataserver2/users/' + user2_username + '/Pages(' + ntiids.ROOT + ')/RecursiveStream' )
		assert_that( res.json_body['Items'], has_length( 1 ) )
		assert_that( res.json_body['Items'][0]['Item'], has_entry( 'title', data['title'] ) )

		# (Though not the non-follower)
		testapp3.get(  '/dataserver2/users/' + user3_username + '/Pages(' + ntiids.ROOT + ')/RecursiveStream', status=404 )

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
			assert_that( items, has_length( 2 ) )
			assert_that( items, contains_inanyorder(
				has_entry( 'title', data['title'] ),
				has_entry( 'title', 'A comment' ) ),
				has_key( 'href' ) )

		# These created notifications to the author...
		# ... both on the socket...
		events = eventtesting.getEvents( chat_interfaces.IUserNotificationEvent )
		assert_that( events, has_length( 3 ) ) # Note that this is three, due to the initial read-conflict-error from the stream cache
		for evt in events:
			assert_that( evt.targets, is_( (user_username,) ) )
			#assert_that( evt.args[0], has_property( 'type', nti_interfaces.SC_CREATED ) )

		# ... and in his UGD stream ...
		res = testapp.get( '/dataserver2/users/' + user_username + '/Pages(' + ntiids.ROOT + ')/RecursiveStream' )
		_has_both_comments( res, items=[change['Item'] for change in res.json_body['Items']] )

		# ... and in the UGD stream of a user following the commentor
		res = user2_followerapp.get( '/dataserver2/users/' + user2_follower_username + '/Pages(' + ntiids.ROOT + ')/RecursiveStream' )
		_has_both_comments( res, items=[change['Item'] for change in res.json_body['Items']] )

		# (who can mute the conversation, never to see it again)
		user2_followerapp.put_json( '/dataserver2/users/' + user2_follower_username,
									 {'mute_conversation': entry_ntiid } )
		# thus removing them from his stream
		res = user2_followerapp.get( '/dataserver2/users/' + user2_follower_username + '/Pages(' + ntiids.ROOT + ')/RecursiveStream', status=404 )

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
			assert_that( sums, contains( '<div><br />' + 'A comment body', '<div><br />' + data['body'][0]) )

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
		res = testapp2.get( '/dataserver2/users/' + user2_username + '/Pages(' + ntiids.ROOT + ')/RecursiveStream', status=404 )

		# ... and the comments vanish from the stream of the other user following the commentor (the one not muted)
		res = user2_follower2app.get( '/dataserver2/users/' + user2_follower2_username + '/Pages(' + ntiids.ROOT + ')/RecursiveStream', status=404 )

		# ... but the commenting user can still see his comments in his activity
		res = testapp2.get( UQ( '/dataserver2/users/' + user2_username + '/Activity' ) )
		_has_both_comments( res )
		# ... as can the original user, since he can still delete them
		res = testapp.get( UQ( '/dataserver2/users/' + user2_username + '/Activity' ) )
		_has_both_comments( res )
		# ... but the other community member cannot
		res = testapp3.get( UQ( '/dataserver2/users/' + user2_username + '/Activity' ) )
		assert_that( res.json_body['Items'], has_length( 0 ) )
		# ... and the actual blog entry is not in the activity of the creating user anymore,
		# as far as the commenting user is concerned
		res = testapp2.get( UQ( '/dataserver2/users/' + user_username + '/Activity' ) )
		assert_that( res.json_body, has_entry( 'Items', is_empty() ) )
		# All of the mod times were updated
		assert_that( res.json_body['Last Modified'], is_( greater_than( user_activity_mod_time_body ) ) )
		assert_that( res.last_modified, is_( datetime.datetime.fromtimestamp( res.json_body['Last Modified'], webob.datetime_utils.UTC ) ) )
		# and a conditional request works too

		res = testapp2.get( UQ( '/dataserver2/users/' + user_username + '/Activity' ), headers={'If-Modified-Since': webob.datetime_utils.serialize_date(user_activity_mod_time)} )
		assert_that( res.json_body, has_entry( 'Items', is_empty() ) )
		testapp2.get( UQ( '/dataserver2/users/' + user_username + '/Activity' ),
					  headers={'If-Modified-Since': webob.datetime_utils.serialize_date(res.last_modified)},
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
		assert_that( res.json_body['Last Modified'], greater_than( content_last_mod ) )
		content_last_mod = res.json_body['Last Modified']
		assert_that( res.last_modified, is_( datetime.datetime.fromtimestamp( content_last_mod, webob.datetime_utils.UTC ) ) )

		# and, if favorited, filtered to the favorites
		for uname, app in ((user_username, testapp), (user2_username, testapp2)):
			app.post( fav_href )
			res = app.get( '/dataserver2/users/' + uname + '/Pages(' + ntiids.ROOT + ')/RecursiveUserGeneratedData',
							   params={'filter': 'Favorite'})
			assert_that( res.json_body['Items'], contains( has_entry( 'title', 'My New Blog' ) ) )
			unfav_href = self.require_link_href_with_rel( res.json_body['Items'][0], 'unfavorite' )

		for uname, app, status in ((user_username, testapp, 200), (user2_username, testapp2, 404)):
			app.post( unfav_href )
			res = app.get( '/dataserver2/users/' + uname + '/Pages(' + ntiids.ROOT + ')/RecursiveUserGeneratedData',
							   params={'filter': 'Favorite'},
							   status=status)
			if status == 200:
				assert_that( res.json_body['Items'], is_empty() )

		# Likewise, favoriting comments works
		for uname, app in ((user_username, testapp), (user2_username, testapp2)):
			app.post( comment2_fav_href )
			res = app.get( '/dataserver2/users/' + uname + '/Pages(' + ntiids.ROOT + ')/RecursiveUserGeneratedData',
							   params={'filter': 'Favorite'})
			assert_that( res.json_body['Items'], contains( has_entry( 'title', comment2_title ) ) )
			unfav_href = self.require_link_href_with_rel( res.json_body['Items'][0], 'unfavorite' )

		for uname, app, status in ((user_username, testapp, 200), (user2_username, testapp2, 404)):
			app.post( unfav_href )
			res = app.get( '/dataserver2/users/' + uname + '/Pages(' + ntiids.ROOT + ')/RecursiveUserGeneratedData',
							   params={'filter': 'Favorite'},
							   status=status)
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
												has_entries( 'Deleted', True,  'title', 'This object has been deleted.' ),
												has_entries( 'Deleted', True,  'title', 'This object has been deleted.' ) ) )

		# and in the metadata
		res = testapp.get( entry_url )
		assert_that( res.json_body, has_entry( 'PostCount', 2 ) )

		# Even though they still exist at the same place, they cannot be used in any way
		testapp2.delete( self.require_link_href_with_rel( comment2res.json_body, 'edit' ), status=404 )
		testapp2.get( self.require_link_href_with_rel( comment2res.json_body, 'edit' ), status=404 )
		testapp2.put_json( self.require_link_href_with_rel( comment2res.json_body, 'edit' ), data, status=404 )

		# They did get removed from the activity stream, however, for all three users
		for app in testapp, testapp2, testapp3:
			res = app.get( UQ( '/dataserver2/users/' + user2_username + '/Activity' ) )
			assert_that( res.json_body['Items'], has_length( 0 ) )

		# As well as the RecursiveStream
		for uname, app, status, length in ((user_username, testapp, 404, 0),
										   (user2_username, testapp2, 200, 1), # He still has the blog notification
										   (user3_username, testapp3, 404, 0)):
			__traceback_info__ = uname
			res = app.get( '/dataserver2/users/' + uname  + '/Pages(' + ntiids.ROOT + ')/RecursiveStream', status=status )
			if status == 200:
				if length == 0:
					assert_that( res.json_body['Items'], is_empty() )
				else:
					assert_that( res.json_body['Items'], has_length(length) )

	@WithSharedApplicationMockDS
	def test_post_canvas_image_in_headline_post_produces_fetchable_link( self ):
		" Images posted as data urls come back as real links which can be fetched "
		with mock_dataserver.mock_db_trans(self.ds):
			user = self._create_user( username='original_user@foo' )
			user2 = self._create_user( username=user.username + '2' )
			# make them share a community
			community = users.Community.create_community( username='TheCommunity' )
			user.join_community( community )
			user2.join_community( community )
			user2_username = user2.username
			user_username = user.username


		testapp = _TestApp( self.app, extra_environ=self._make_extra_environ(username=user_username) )
		testapp2 = _TestApp( self.app, extra_environ=self._make_extra_environ(username=user2_username) )


		canvas_data = {u'Class': 'Canvas',
					   'ContainerId': 'tag:foo:bar',
					   u'MimeType': u'application/vnd.nextthought.canvas',
					   'shapeList': [{u'Class': 'CanvasUrlShape',
									  u'MimeType': u'application/vnd.nextthought.canvasurlshape',
									  u'url': u'data:image/gif;base64,R0lGODlhCwALAIAAAAAA3pn/ZiH5BAEAAAEALAAAAAALAAsAAAIUhA+hkcuO4lmNVindo7qyrIXiGBYAOw=='}]}

		data = { 'Class': 'Post',
				 'title': 'My New Blog',
				 'body': ['My first thought', canvas_data] }

		# Create the blog
		res = testapp.post_json( '/dataserver2/users/' + user_username + '/Blog', data )
		entry_ntiid = res.json_body['NTIID']
		pub_url = self.require_link_href_with_rel( res.json_body, 'publish' )

		def _check_canvas( res, canvas, acc_to_other=False ):
			assert_that( canvas, has_entry( 'shapeList', has_length( 1 ) ) )
			assert_that( canvas, has_entry( 'shapeList', contains( has_entry( 'Class', 'CanvasUrlShape' ) ) ) )
			assert_that( canvas, has_entry( 'shapeList', contains( has_entry( 'url', contains_string( '/dataserver2/' ) ) ) ) )


			res = testapp.get( canvas['shapeList'][0]['url'] )
			# The content type is preserved
			assert_that( res, has_property( 'content_type', 'image/gif' ) )
			# The modified date is the same as the canvas containing it
			assert_that( res, has_property( 'last_modified', not_none() ) )
		#	assert_that( res, has_property( 'last_modified', canvas_res.last_modified ) )
			# It either can or cannot be accessed by another user
			testapp2.get( canvas['shapeList'][0]['url'], status=(200 if acc_to_other else 403) )

		_check_canvas( res, res.json_body['headline']['body'][1] )

		# If we "edit" the headline, then nothing breaks
		headline_edit_link = self.require_link_href_with_rel( res.json_body['headline'], 'edit' )

		res = testapp.put_json( headline_edit_link, res.json_body['headline'] )
		_check_canvas( res, res.json_body['body'][1] )

		from nti.dataserver.site import get_site_for_site_names
		from zope import component
		from zope.component.hooks import site
		with mock_dataserver.mock_db_trans(self.ds):
			with site( get_site_for_site_names( ('alpha.nextthought.com',) ) ):
				user = users.User.get_user( user_username )
				assert_that( component.queryAdapter( user, frm_interfaces.IPersonalBlog ), not_none() )
				__traceback_info__ = entry_ntiid
				entry = ntiids.find_object_with_ntiid( entry_ntiid )
				assert_that( entry, is_( not_none() ) )
				canvas = entry.headline.body[1]
				url_shape = canvas.shapeList[0]
				# And it externalizes as a real link because it owns the file data
				assert_that( url_shape.toExternalObject()['url'], ends_with( '@@view' ) )

		# When published, it is visible to the other user
		testapp.post( pub_url )
		_check_canvas( res, res.json_body['body'][1], acc_to_other=True )


class TestApplicationCommunityForums(_AbstractTestApplicationForums):

	features = SharedApplicationTestBase.features + ('forums',)
	default_community = 'TheCommunity'
	default_entityname = default_community
	forum_url_relative_to_user = 'Forum'
	forum_ntiid = 'tag:nextthought.com,2011-10:TheCommunity-Forum:GeneralCommunity-Forum'
	forum_topic_ntiid_base = 'tag:nextthought.com,2011-10:TheCommunity-Topic:GeneralCommunity-'

	forum_content_type = 'application/vnd.nextthought.forums.communityforum+json'
	forum_headline_class_type = 'Post'
	forum_topic_content_type = CommunityHeadlineTopic.mimeType + '+json'
	forum_link_rel = 'Forum'
	forum_title = forum_link_rel
	forum_type = CommunityForum

	forum_topic_comment_content_type = 'application/vnd.nextthought.forums.generalforumcomment+json'

	@WithSharedApplicationMockDS(users=True,testapp=True)
	def test_user_can_POST_new_forum_entry_class( self ):
		"""POSTing an IPost to the forum URL automatically creates a new topic"""

		# With a Class value:
		data = { 'Class': self.forum_headline_class_type,
				 'title': 'My New Blog',
				 'body': ['My first thought'] }

		self._do_test_user_can_POST_new_forum_entry( data )


	def _do_test_user_can_POST_new_forum_entry( self, data, content_type=None, status_only=None, expected_data=None ):
		res = self._do_simple_tests_for_POST_of_topic_entry( data, content_type=content_type, status_only=status_only, expected_data=expected_data )
		if status_only:
			return res
		testapp = self.testapp

		# Returns the representation of the new topic created
		data = expected_data or data
		contents_href = self.require_link_href_with_rel( res.json_body, 'contents' )
		entry_id = res.json_body['ID']
		headline_json = res.json_body['headline']

		entry_url = res.location
		entry_ntiid = res.json_body['NTIID']

		# The new topic is accessible at its OID URL, its pretty URL, and by NTIID (not yet)
		for url in entry_url, UQ( '/dataserver2/users/TheCommunity/Forum/' + entry_id ):  #, UQ( '/dataserver2/NTIIDs/' + entry_ntiid ):
			testapp.get( url )


		# and it has no contents
		testapp.get( contents_href, status=200 )

		# It shows up in the blog contents
		res = testapp.get( '/dataserver2/users/TheCommunity/Forum/contents' )
		blog_items = res.json_body['Items']
		assert_that( blog_items, contains( has_entry( 'title', data['title'] ) ) )
		# With its links all intact
		blog_item = blog_items[0]
		assert_that( blog_item, has_entry( 'href', UQ( '/dataserver2/users/TheCommunity/Forum/' + blog_item['ID'] ) ))
		self.require_link_href_with_rel( blog_item, 'contents' )
		#self.require_link_href_with_rel( blog_item, 'like' ) # entries can be liked
		#self.require_link_href_with_rel( blog_item, 'flag' ) # entries can be flagged
		#self.require_link_href_with_rel( blog_item, 'edit' ) # entries can be 'edited' (actually they cannot)


		# It also shows up in the blog's data feed (partially rendered in HTML)
		res = testapp.get( '/dataserver2/users/TheCommunity/Forum/feed.atom' )
		assert_that( res.content_type, is_( 'application/atom+xml'))
		res._use_unicode = False
		pq = PyQuery( res.body, parser='html', namespaces={u'atom': u'http://www.w3.org/2005/Atom'} ) # html to ignore namespaces. Sigh.
		assert_that( pq( b'entry title' ).text(), is_( data['title'] ) )
		assert_that( pq( b'entry summary' ).text(), is_( '<div><br />' + data['body'][0] ) )


		# And in the user activity view
		#res = testapp.get( '/dataserver2/users/sjohnson@nextthought.com/Activity' )
		#assert_that( res.json_body['Items'], contains( has_entry( 'title', data['title'] ) ) )
		#assert_that( res.json_body['Items'], has_length( 1 ) ) # make sure no dups

		# And in the user root recursive data stream
		#res = testapp.get( '/dataserver2/users/sjohnson@nextthought.com/Pages(' + ntiids.ROOT + ')/RecursiveUserGeneratedData' )
		#assert_that( res.json_body['Items'], contains( has_entry( 'title', data['title'] ) ) )

		# and, if favorited, filtered to the favorites
		#testapp.post( fav_href )
		#res = testapp.get( '/dataserver2/users/sjohnson@nextthought.com/Pages(' + ntiids.ROOT + ')/RecursiveUserGeneratedData',
		#				   params={'filter': 'Favorite'})
		#assert_that( res.json_body['Items'], contains( has_entry( 'title', data['title'] ) ) )
		#self.require_link_href_with_rel( res.json_body['Items'][0], 'unfavorite' )
