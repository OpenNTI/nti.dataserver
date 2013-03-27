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
from hamcrest import has_entry
from hamcrest import has_property
from hamcrest import has_length
from hamcrest import has_key

from zope.component import eventtesting
from zope.lifecycleevent import IObjectRemovedEvent
from zope.intid.interfaces import IIntIdRemovedEvent


from nti.dataserver.contenttypes.forums.topic import  CommunityHeadlineTopic
from nti.dataserver.contenttypes.forums.forum import CommunityForum
_FORUM_NAME = CommunityForum.__default_name__
from nti.dataserver.contenttypes.forums.board import CommunityBoard
_BOARD_NAME = CommunityBoard.__default_name__


from nti.appserver.tests.test_application import SharedApplicationTestBase
from nti.appserver.tests.test_application import WithSharedApplicationMockDSHandleChanges as WithSharedApplicationMockDS
from nti.appserver.tests.test_application import _TestApp

from pyquery import PyQuery
from urllib import quote as UQ

# TODO: FIXME: This solves an order-of-imports issue, where
# mimeType fields are only added to the classes when externalization is
# loaded (usually with ZCML, so in practice this is not a problem,
# but statically and in isolated unit-tests, it could be)
from nti.dataserver.contenttypes.forums import externalization as frm_ext
frm_ext = frm_ext


from .base_forum_testing import AbstractTestApplicationForumsBase
from .base_forum_testing import UserCommunityFixture
from .base_forum_testing import _plain


class TestApplicationCommunityForums(AbstractTestApplicationForumsBase):
	__test__ = True

	features = SharedApplicationTestBase.features + ('forums',)
	extra_environ_default_user = AbstractTestApplicationForumsBase.default_username
	default_community = 'TheCommunity'
	default_entityname = default_community
	forum_url_relative_to_user = _BOARD_NAME + '/' + _FORUM_NAME
	forum_ntiid = 'tag:nextthought.com,2011-10:TheCommunity-Forum:GeneralCommunity-Forum'
	forum_topic_ntiid_base = 'tag:nextthought.com,2011-10:TheCommunity-Topic:GeneralCommunity-Forum.'

	board_ntiid = 'tag:nextthought.com,2011-10:TheCommunity-Board:GeneralCommunity-DiscussionBoard'
	board_content_type = CommunityBoard.mimeType + '+json'

	forum_content_type = 'application/vnd.nextthought.forums.communityforum+json'
	forum_headline_class_type = 'Post'
	forum_topic_content_type = CommunityHeadlineTopic.mimeType + '+json'
	board_link_rel = forum_link_rel = _BOARD_NAME
	forum_title = _FORUM_NAME
	forum_type = CommunityForum

	forum_topic_comment_content_type = 'application/vnd.nextthought.forums.generalforumcomment+json'

	def setUp( self ):
		super(TestApplicationCommunityForums,self).setUp()
		self.board_pretty_url = self.forum_pretty_url[:-(len(_FORUM_NAME) + 1)]

	@WithSharedApplicationMockDS(users=True,testapp=True)
	def test_default_board_in_links( self ):
		# Default board is present in the community links
		user = self.resolve_user(username=self.default_community)
		href = self.require_link_href_with_rel( user, self.board_link_rel )
		assert_that( href, is_( self.board_pretty_url ) )

	@WithSharedApplicationMockDS(users=True,testapp=True)
	def test_default_board_contents( self ):
		# default board has a contents href which can be fetched,
		# returning the default forum
		community = self.resolve_user(username=self.default_community)
		board_href = self.require_link_href_with_rel( community, self.board_link_rel )

		board_res = self.testapp.get( board_href )
		assert_that( board_res, has_property( 'content_type', self.board_content_type ) )
		assert_that( board_res.json_body, has_entry( 'MimeType', _plain( self.board_content_type ) ) )
		assert_that( board_res.json_body, has_entry( 'NTIID', self.board_ntiid ) )
		assert_that( board_res.json_body, has_entry( 'href', self.board_pretty_url ) )
		contents_href = self.require_link_href_with_rel( board_res.json_body, 'contents' )

		contents_res = self.testapp.get( contents_href )
		assert_that( contents_res.json_body, has_entry( 'Items', has_length( 1 ) ) )
		assert_that( contents_res.json_body['Items'][0], has_entry( 'MimeType', _plain( self.forum_content_type ) ) )

	@WithSharedApplicationMockDS(users=True,testapp=True)
	def test_default_board_can_be_resolved_by_ntiid( self ):

		board_res = self.fetch_by_ntiid( self.board_ntiid )
		assert_that( board_res, has_property( 'content_type', self.board_content_type ) )
		assert_that( board_res.json_body, has_entry( 'MimeType', _plain( self.board_content_type ) ) )
		assert_that( board_res.json_body, has_entry( 'NTIID', self.board_ntiid ) )
		self.require_link_href_with_rel( board_res.json_body, 'contents' )


	@WithSharedApplicationMockDS(users=True,testapp=True)
	def test_normal_user_cannot_post_to_board(self):
		# attempting to do so gets you DENIED
		self.testapp.post_json( self.board_pretty_url, self._create_post_data_for_POST(), status=403 )


	@WithSharedApplicationMockDS(users=('sjohnson@nextthought.com',),testapp=True)
	def test_super_user_can_post_to_board_to_create_forum(self):
		# relying on @nextthought.com automatically being an admin
		adminapp = _TestApp( self.app, extra_environ=self._make_extra_environ(username='sjohnson@nextthought.com') )
		forum_data = self._create_post_data_for_POST()
		# Incoming mimetype is actually unimportant at this point
		del forum_data['Class']
		del forum_data['MimeType']
		forum_res = adminapp.post_json( self.board_pretty_url, forum_data, status=201 )

		# Which creates a forum
		assert_that( forum_res, has_property( 'content_type', self.forum_content_type ) )
		forum_url = self.board_pretty_url + '/' + forum_res.json_body['ID']
		assert_that( forum_res.json_body, has_entry( 'href', forum_url ) )
		assert_that( forum_res, has_property( 'location', 'http://localhost' + forum_url + '/' ) )
		assert_that( forum_res.json_body, has_entry( 'ContainerId', self.board_ntiid ) )
		self.require_link_href_with_rel( forum_res.json_body, 'edit' )
		assert_that( forum_res.json_body, has_entry( 'title', forum_data['title'] ) )
		assert_that( forum_res.json_body, has_entry( 'description', forum_data['description'] ) )

	@WithSharedApplicationMockDS(users=('sjohnson@nextthought.com',),testapp=True,default_authenticate=True)
	def test_super_user_can_edit_forum_description(self):
		# relying on @nextthought.com automatically being an admin
		adminapp = _TestApp( self.app, extra_environ=self._make_extra_environ(username='sjohnson@nextthought.com') )
		forum_data = self._create_post_data_for_POST()
		forum_res = adminapp.post_json( self.board_pretty_url, forum_data, status=201 )

		adminapp.put_json( forum_res.location, {'description': 'The updated description'} )

		forum_res = self.testapp.get( forum_res.location )
		assert_that( forum_res.json_body, has_entry( 'description', "The updated description" ) )

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

		# It shows up in the blog contents
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
		assert_that( pq( b'entry summary' ).text(), is_( '<div><br />' + data['body'][0] ) )

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

		# non-creator adds comment
		comment_data = self._create_comment_data_for_POST()
		testapp2.post_json( topic_url, comment_data, status=201 )

		# the creator gets the comment, but not the topic in his stream (because he created it)
		res = self.fetch_user_root_rstream( testapp, fixture.user_username )
		assert_that( res.json_body, has_entry( 'TotalItemCount', 1 ) )
		assert_that( res.json_body['Items'][0], has_entry( 'ChangeType', 'Created' ) )


		# the commentor gets the topic created by the other user (as Modified)
		res = self.fetch_user_root_rstream( testapp2, fixture.user2_username )#, status=404 )
		assert_that( res.json_body, has_entry( 'TotalItemCount', 1 ) )
		assert_that( res.json_body['Items'][0], has_entry( 'ChangeType', 'Modified' ) )

		# The creator gets the topic he created in his UGD,
		# but not the comment (???)
		res = self.fetch_user_root_rugd( testapp, fixture.user_username )
		assert_that( res.json_body, has_entry( 'TotalItemCount', 1 ) )

		# The commentor also gets just the topic in his UGD
		res = self.fetch_user_root_rugd( testapp2, fixture.user2_username )
		assert_that( res.json_body, has_entry( 'TotalItemCount', 1 ) )
