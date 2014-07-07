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
from hamcrest import is_
from hamcrest import is_not as does_not
is_not = does_not
from hamcrest import contains
from hamcrest import has_item
from hamcrest import has_entry
from hamcrest import has_entries
from hamcrest import has_property
from hamcrest import has_length
from hamcrest import has_key
from hamcrest import greater_than

from nti.testing.time import time_monotonically_increases

from zope.component import eventtesting
from zope.lifecycleevent import IObjectRemovedEvent
from zope.intid.interfaces import IIntIdRemovedEvent


from nti.dataserver.contenttypes.forums.topic import  CommunityHeadlineTopic
from nti.dataserver.contenttypes.forums.forum import CommunityForum
_FORUM_NAME = CommunityForum.__default_name__
from nti.dataserver.contenttypes.forums.board import CommunityBoard
_BOARD_NAME = CommunityBoard.__default_name__


from nti.app.testing.application_webtest import ApplicationLayerTest
from nti.app.testing.decorators import WithSharedApplicationMockDSHandleChanges as WithSharedApplicationMockDS
from nti.app.testing.webtest import TestApp as _TestApp

from pyquery import PyQuery
from urllib import quote as UQ

# TODO: FIXME: This solves an order-of-imports issue, where
# mimeType fields are only added to the classes when externalization is
# loaded (usually with ZCML, so in practice this is not a problem,
# but statically and in isolated unit-tests, it could be)
from nti.dataserver.contenttypes.forums import externalization as frm_ext
frm_ext = frm_ext


from .base_forum_testing import AbstractTestApplicationForumsBaseMixin
from .base_forum_testing import UserCommunityFixture
from .base_forum_testing import _plain


class TestApplicationCommunityForums(AbstractTestApplicationForumsBaseMixin,ApplicationLayerTest):
	__test__ = True

	extra_environ_default_user = AbstractTestApplicationForumsBaseMixin.default_username
	default_community = 'TheCommunity'
	default_entityname = default_community
	forum_url_relative_to_user = _BOARD_NAME + '/' + _FORUM_NAME
	forum_ntiid = 'tag:nextthought.com,2011-10:TheCommunity-Forum:GeneralCommunity-Forum'
	forum_topic_ntiid_base = 'tag:nextthought.com,2011-10:TheCommunity-Topic:GeneralCommunity-Forum.'

	board_ntiid = 'tag:nextthought.com,2011-10:TheCommunity-Board:GeneralCommunity-DiscussionBoard'
	board_ntiid_checker = board_ntiid
	board_content_type = None

	forum_content_type = 'application/vnd.nextthought.forums.communityforum+json'
	forum_headline_class_type = 'Post'
	forum_topic_content_type = None
	board_link_rel = forum_link_rel = _BOARD_NAME
	forum_title = _FORUM_NAME
	forum_type = CommunityForum

	forum_topic_comment_content_type = 'application/vnd.nextthought.forums.generalforumcomment+json'

	def setUp( self ):
		super(TestApplicationCommunityForums,self).setUp()
		self.board_pretty_url = self.forum_pretty_url[:-(len(_FORUM_NAME) + 1)]

		self.board_content_type = CommunityBoard.mimeType + '+json'
		self.forum_topic_content_type = CommunityHeadlineTopic.mimeType + '+json'

	@WithSharedApplicationMockDS(users=True,testapp=True)
	def test_default_board_in_links( self ):
		# Default board is present in the community links
		user = self.resolve_user(username=self.default_community)
		href = self.require_link_href_with_rel( user, self.board_link_rel )
		assert_that( href, is_( self.board_pretty_url ) )


	@WithSharedApplicationMockDS(users=True,testapp=True)
	def test_default_board_can_be_resolved_by_ntiid( self ):

		board_res = self.fetch_by_ntiid( self.board_ntiid )
		assert_that( board_res, has_property( 'content_type', self.board_content_type ) )
		assert_that( board_res.json_body, has_entry( 'MimeType', _plain( self.board_content_type ) ) )
		assert_that( board_res.json_body, has_entry( 'NTIID', self.board_ntiid ) )
		self.require_link_href_with_rel( board_res.json_body, 'contents' )

	@WithSharedApplicationMockDS(users=('sjohnson@nextthought.com',),testapp=True,default_authenticate=True)
	@time_monotonically_increases
	def test_super_user_can_edit_forum_description(self):
		# relying on @nextthought.com automatically being an admin
		adminapp = _TestApp( self.app, extra_environ=self._make_extra_environ(username='sjohnson@nextthought.com') )
		forum_data = self._create_post_data_for_POST()
		forum_res = adminapp.post_json( self.board_pretty_url, forum_data, status=201 )

		board_res = adminapp.get( self.board_pretty_url )
		board_contents = self.require_link_href_with_rel(board_res.json_body, 'contents')
		board_contents_res = adminapp.get(board_contents)

		adminapp.put_json( forum_res.location, {'description': 'The updated description'} )

		forum_res = self.testapp.get( forum_res.location )
		assert_that( forum_res.json_body, has_entry( 'description', "The updated description" ) )

		# And when we get the board again, it shows up as changed
		adminapp.get( board_contents,
					  headers={b'If-None-Match': board_contents_res.etag,
							   b'If-Modified-Since': board_contents_res.headers['Last-Modified']},
					  status=200)

	@WithSharedApplicationMockDS(users=('sjohnson@nextthought.com',),testapp=True,default_authenticate=True)
	def test_super_user_can_edit_forum_description_using_field(self):
		# relying on @nextthought.com automatically being an admin
		adminapp = _TestApp( self.app, extra_environ=self._make_extra_environ(username='sjohnson@nextthought.com') )
		forum_data = self._create_post_data_for_POST()
		forum_res = adminapp.post_json( self.board_pretty_url, forum_data, status=201 )

		adminapp.put_json( forum_res.location + '++fields++description', 'The updated description' )

		forum_res = self.testapp.get( forum_res.location )
		assert_that( forum_res.json_body, has_entry( 'description', "The updated description" ) )

	@WithSharedApplicationMockDS(users=('sjohnson@nextthought.com',),testapp=True,default_authenticate=True)
	def test_super_user_can_delete_forum(self):
		# relying on @nextthought.com automatically being an admin
		adminapp = _TestApp( self.app, extra_environ=self._make_extra_environ(username='sjohnson@nextthought.com') )
		forum_data = self._create_post_data_for_POST()
		forum_res = adminapp.post_json( self.board_pretty_url, forum_data, status=201 )

		# Normal user cannot
		self.testapp.delete( forum_res.location, status=403 )

		# admin can
		eventtesting.clearEvents()
		adminapp.delete( forum_res.location, status=204 )

		rem_events = eventtesting.getEvents(IObjectRemovedEvent)
		assert_that( rem_events, has_length( 1 ) )
		self.testapp.get( forum_res.location, status=404 )


	@WithSharedApplicationMockDS(users=('sjohnson@nextthought.com',),testapp=True,default_authenticate=True)
	def test_super_user_can_delete_forum_with_topic_and_comments(self):
		# relying on @nextthought.com automatically being an admin
		adminapp = _TestApp( self.app, extra_environ=self._make_extra_environ(username='sjohnson@nextthought.com') )
		forum_data = self._create_post_data_for_POST()
		forum_res = adminapp.post_json( self.board_pretty_url, forum_data, status=201 )

		# now community user publishes
		publish_res, _ = self._POST_and_publish_topic_entry( forum_url=forum_res.location )

		# and for grins, community user comments on own topic
		comment_res = self.testapp.post_json( publish_res.json_body['href'], self._create_comment_data_for_POST() )

		# now the admin can delete the forum, destroying the forum,
		# the topic, the headline post, and the comment
		eventtesting.clearEvents()
		adminapp.delete( forum_res.location, status=204 )
		# There's only one ObjectRemovedEvent, but it is dispatched
		# to all the sublocations
		rem_events = eventtesting.getEvents(IObjectRemovedEvent)
		assert_that( rem_events, has_length( 1 ) )

		# So all four of the objects got their intid removed
		int_rem_events = eventtesting.getEvents(IIntIdRemovedEvent)
		assert_that( int_rem_events, has_length( 4 ) )
		# So all the locations 404
		for res in forum_res, publish_res, comment_res:
			self.testapp.get( res.location, status=404 )
		# and nothing is searchable
		for term in self.forum_comment_unique, self.forum_headline_unique:
			search_res = self.search_user_rugd( term )
			assert_that( search_res.json_body, has_entry( 'Hit Count', 0 ) )

	def _do_test_user_can_POST_new_forum_entry( self, data, content_type=None, status_only=None, expected_data=None ):
		# Override the method in super()
		activity_res = self.fetch_user_activity()
		post_res = self._do_simple_tests_for_POST_of_topic_entry( data, content_type=content_type, status_only=status_only, expected_data=expected_data )
		if status_only:
			return post_res
		testapp = self.testapp
		res = post_res
		# Returns the representation of the new topic created
		data = expected_data or data
		contents_href = self.require_link_href_with_rel( res.json_body, 'contents' )
		entry_id = res.json_body['ID']
		assert_that( res.json_body, has_key( 'headline' ) )
		entry_url = res.location
		entry_ntiid = res.json_body['NTIID']

		# The new topic is accessible at its OID URL, its pretty URL, and by NTIID
		for url in entry_url, self.forum_topic_href( entry_id ), UQ( '/dataserver2/NTIIDs/' + entry_ntiid ):
			testapp.get( url )

		# and it has no contents
		testapp.get( contents_href, status=200 )

		# It shows up in the forum contents
		res = testapp.get( self.forum_pretty_contents_url )
		blog_items = res.json_body['Items']
		assert_that( blog_items, contains( has_entry( 'title', data['title'] ) ) )
		# With its links all intact
		blog_item = blog_items[0]
		assert_that( blog_item, has_entry( 'href', self.forum_topic_href( blog_item['ID'] ) ))
		self.require_link_href_with_rel( blog_item, 'contents' )

		# It also shows up in the blog's data feed (partially rendered in HTML)
		res = testapp.get( self.forum_pretty_url + '/feed.atom' )
		assert_that( res.content_type, is_( 'application/atom+xml'))
		res._use_unicode = False
		pq = PyQuery( res.body, parser='html', namespaces={u'atom': u'http://www.w3.org/2005/Atom'} ) # html to ignore namespaces. Sigh.
		assert_that( pq( b'entry title' ).text(), is_( data['title'] ) )
		assert_that( pq( b'entry summary' ).text(), is_( '<div><br />' + data['body'][0] + '</div>' ) )

		# It shows up in the activity stream for the creator, and
		# the modification date and etag of the data changed
		new_activity_res = self.fetch_user_activity()
		assert_that( new_activity_res.json_body['Items'], has_item(has_entry('NTIID', entry_ntiid)))
		assert_that( new_activity_res.last_modified, is_( greater_than( activity_res.last_modified )))
		assert_that( new_activity_res.etag, is_not(activity_res.etag))
		return post_res

	@WithSharedApplicationMockDS
	def test_creator_cannot_DELETE_community_user_comment_in_published_topic(self):
		fixture = UserCommunityFixture( self )
		self.testapp = testapp = fixture.testapp
		testapp2 = fixture.testapp2

		publish_res, _ = self._POST_and_publish_topic_entry()
		topic_url = publish_res.location

		# non-creator comment
		comment_data = self._create_comment_data_for_POST()
		comment_res = testapp2.post_json( topic_url, comment_data, status=201 )
		edit_href = self.require_link_href_with_rel( comment_res.json_body, 'edit' )

		# cannot be deleted by creator
		testapp.delete( edit_href, status=403 ) # forbidden by ACL

	@WithSharedApplicationMockDS
	def test_community_topics_and_comments_in_RUGD_and_RSTREAM(self):
		fixture = UserCommunityFixture( self )
		self.testapp = testapp = fixture.testapp
		testapp2 = fixture.testapp2

		publish_res, _ = self._POST_and_publish_topic_entry()
		topic_url = publish_res.location

		# The creator of the community topic doesn't see it in his RUGD
		# without applying some filters
		self.fetch_user_root_rugd( testapp, fixture.user_username, status=404 )

		res = self.fetch_user_root_rugd(testapp, fixture.user_username,
										params={'filter': 'MeOnly',
												'accept': 'application/vnd.nextthought.forums.communityheadlinetopic'})
		assert_that(res.json_body, has_entry('FilteredTotalItemCount', 1))
		assert_that(res.json_body, has_entry('TotalItemCount', 2)) # Both topic and comment
		assert_that(res.json_body['Items'], has_item(has_entry('title', publish_res.json_body['title'])) )

		# Now, the non-creator has the topic in his stream as created
		res = self.fetch_user_root_rstream( testapp2, fixture.user2_username )
		assert_that( res.json_body, has_entry( 'TotalItemCount', 1 ) )
		assert_that( res.json_body['Items'][0], has_entry( 'ChangeType', 'Shared' ) )
		created_event_time = res.json_body['Items'][0]['Last Modified']

		# non-creator adds comment
		comment_data = self._create_comment_data_for_POST()
		testapp2.post_json( topic_url, comment_data, status=201 )

		# the creator gets the comment, but not the topic in his stream (because he created it)
		res = self.fetch_user_root_rstream( testapp, fixture.user_username )
		assert_that( res.json_body, has_entry( 'TotalItemCount', 1 ) )
		assert_that( res.json_body['Items'][0], has_entry( 'ChangeType', 'Created' ) )

		# For the commenter, the comment did not change the event in the stream for the topic, it stays
		# exactly the same
		res = self.fetch_user_root_rstream( testapp2, fixture.user2_username )#, status=404 )
		assert_that( res.json_body, has_entry( 'TotalItemCount', 1 ) )
		assert_that( res.json_body['Items'][0], has_entries( 'ChangeType', 'Shared',
															 'Last Modified', created_event_time ) )


		# The creator of the topic never sees it in his RUGD, not
		# even after a comment is added
		self.fetch_user_root_rugd( testapp, fixture.user_username, status=404 )

		# The commentor also has neither the topic he didn't create,
		# nor the comment he did create, in his RUGD, without applying filters
		self.fetch_user_root_rugd( testapp2, fixture.user2_username, status=404 )

		res = self.fetch_user_root_rugd( testapp2, fixture.user2_username, params={'filter': 'MeOnly'})
		assert_that( res.json_body, has_entry('TotalItemCount', 1) )


	@WithSharedApplicationMockDS(users=True,testapp=True)
	def test_creator_cannot_change_sharing_on_community_topic( self ):
		#""" Sharing is fixed and cannot be changed for a blog entry, its story, or a comment"""

		testapp = self.testapp
		res = self._POST_topic_entry()

		topic_url = res.location
		self.require_link_href_with_rel(res.json_body['headline'], 'edit')

		eventtesting.clearEvents()

		# Field updates
		# Cannot change the entry
		testapp.put_json( topic_url + '/++fields++sharedWith',
						  ['Everyone'],
						  # Because of the way traversal is right now, this results in a 404,
						  # when really we want a 403
						  status=404)
		# Nor when putting the whole thing
		# The entry itself simply cannot be modified (predicate mismatch right now)
		testapp.put_json( topic_url,
						  {'sharedWith': ['Everyone']},
						  status=403 )

	@WithSharedApplicationMockDS
	@time_monotonically_increases
	def test_contents_of_forum_last_modified_changes_when_new_topic_added_published(self):
		fixture = UserCommunityFixture( self )
		self.testapp = fixture.testapp

		self._POST_and_publish_topic_entry()
		forum_res = self.testapp.get( self.forum_pretty_url )
		forum_contents_href = self.require_link_href_with_rel( forum_res.json_body, 'contents' )

		forum_contents_res = self.testapp.get( forum_contents_href )
		assert_that( forum_contents_res.json_body, has_entry( 'TotalItemCount', 1 ) )

		self._POST_and_publish_topic_entry() # create a second one

		forum_contents_res2 = self.testapp.get( forum_contents_href,
												headers={b'If-None-Match': forum_contents_res.etag,
														 b'If-Modified-Since': forum_contents_res.headers['Last-Modified']},
												status=200)

		assert_that( forum_contents_res2.json_body, has_entry( 'TotalItemCount', 2 ) )

		forum_contents_res3 = self.testapp.get( forum_contents_href,
												params={b'searchTerm': 'notfound'},
												status=200)

		assert_that(forum_contents_res3.json_body, has_entry('FilteredTotalItemCount', 0))

		forum_contents_res3 = self.testapp.get(forum_contents_href,
											   params={b'searchTerm': 'blog'},
											   status=200)

		assert_that(forum_contents_res3.json_body, has_entry(u'TotalItemCount', 2))

	@WithSharedApplicationMockDS
	@time_monotonically_increases
	def test_contents_of_forum_last_modified_changes_when_new_topic_title_changed(self):
		fixture = UserCommunityFixture( self )
		self.testapp = fixture.testapp

		topic_res, _ = self._POST_and_publish_topic_entry()
		forum_res = self.testapp.get( self.forum_pretty_url )
		forum_contents_href = self.require_link_href_with_rel( forum_res.json_body, 'contents' )

		forum_contents_res = self.testapp.get( forum_contents_href )
		assert_that( forum_contents_res.json_body, has_entry( 'TotalItemCount', 1 ) )

		self.testapp.put_json( topic_res.json_body['headline']['href'], {'title': "A new and different title"} )

		forum_contents_res2 = self.testapp.get( forum_contents_href,
												headers={b'If-None-Match': forum_contents_res.etag,
														 b'If-Modified-Since': forum_contents_res.headers['Last-Modified']},
												status=200)

	@WithSharedApplicationMockDS
	@time_monotonically_increases
	def test_contents_of_board_last_modified_changes_when_new_topic_added_to_forum(self):
		fixture = UserCommunityFixture( self )
		self.testapp = fixture.testapp

		board_pretty_url = '/dataserver2/users/' + self.default_entityname + '/' + _BOARD_NAME

		self._POST_and_publish_topic_entry()
		board_res = self.testapp.get( board_pretty_url )
		board_contents_href = self.require_link_href_with_rel( board_res.json_body, 'contents' )

		board_contents_res = self.testapp.get( board_contents_href )
		assert_that( board_contents_res.json_body, has_entry( 'TotalItemCount', 1 ) )

		self._POST_and_publish_topic_entry() # create a second one

		board_contents_res2 = self.testapp.get( board_contents_href,
												headers={b'If-None-Match': board_contents_res.etag,
														 b'If-Modified-Since': board_contents_res.headers['Last-Modified']},
												status=200)

		assert_that( board_contents_res2.json_body, has_entry( 'TotalItemCount', 1 ) )
