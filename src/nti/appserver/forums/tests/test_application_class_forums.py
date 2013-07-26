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

from hamcrest import assert_that, has_item, has_entry
from hamcrest import is_not as does_not
is_not = does_not

from nti.dataserver import users
from nti.dataserver.tests import mock_dataserver

from nti.dataserver.contenttypes.forums.board import ClassBoard
from nti.dataserver.contenttypes.forums.forum import ClassForum
from nti.dataserver.contenttypes.forums.topic import ClassHeadlineTopic
from nti.dataserver.contenttypes.forums import interfaces as frm_interaces

from nti.appserver.tests.test_application import SharedApplicationTestBase
from nti.appserver.tests.test_application import WithSharedApplicationMockDSHandleChanges as WithSharedApplicationMockDS

from nti.tests import time_monotonically_increases

from .base_forum_testing import AbstractTestApplicationForumsBase

class TestApplicationClassForum(AbstractTestApplicationForumsBase):
	__test__ = False

	features = SharedApplicationTestBase.features + ('forums',)

	default_username = AbstractTestApplicationForumsBase.default_username  # 'original_user@foo'  # Not an admin user by default 'sjohnson@nextthought.com'
	default_entityname = default_username
	extra_environ_default_user = default_username

	board_name = ClassBoard.__default_name__
	board_content_type = ClassBoard.mimeType + '+json'
	board_ntiid = 'tag:nextthought.com,2011-10:' + extra_environ_default_user + '-Board:Class-' + board_name

	forum_name = 'CS1313'
	forum_type = ClassForum
	forum_link_rel = forum_name
	forum_url_relative_to_user = ClassBoard.__default_name__ + '/' + forum_name

	forum_content_type = 'application/vnd.nextthought.forums.classforum+json'
	forum_headline_class_type = 'Post'
	board_link_rel = forum_link_rel = board_name
	forum_topic_content_type = ClassHeadlineTopic.mimeType + '+json'
	forum_topic_ntiid_base = 'tag:nextthought.com,2011-10:' + extra_environ_default_user + '-Forum:Class-'

	forum_topic_comment_content_type = 'application/vnd.nextthought.forums.classforumcomment+json'
		
	def setUp(self):
		super(TestApplicationClassForum, self).setUp()
		self.board_pretty_url = self.forum_pretty_url[:-(len(self.forum_name) + 1)]

	def _prepare_cs1313_forum(self):
		with mock_dataserver.mock_db_trans(self.ds):
			user = users.User.get_user(self.extra_environ_default_user)
			board = frm_interaces.IClassBoard(user)
			forum = ClassForum()
			forum.creator = user
			forum.title = self.forum_name
			forum.__name__ = forum.__default_name__ = self.forum_name
			board[forum.__default_name__] = forum
			
	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_user_has_classboard_in_service_doc(self):
		self._prepare_cs1313_forum()
		service_doc = self.fetch_service_doc( ).json_body
		[collections] = [x['Items'] for x in service_doc['Items'] if x['Title'] == self.default_username]
		assert_that(collections, has_item(has_entry('Title', self.board_name)))

	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_entity_has_default_forum(self):
		self._prepare_cs1313_forum()
		super(TestApplicationClassForum, self).test_entity_has_default_forum()

	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_user_cannot_POST_new_forum_entry_to_pages(self):
		self._prepare_cs1313_forum()
		super(TestApplicationClassForum, self).test_user_cannot_POST_new_forum_entry_to_pages()

	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_user_can_POST_new_forum_entry_and_flagging_returns_same_href(self):
		self._prepare_cs1313_forum()
		super(TestApplicationClassForum, self).test_user_can_POST_new_forum_entry_and_flagging_returns_same_href()

	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_user_can_POST_new_forum_entry_header_only(self):
		self._prepare_cs1313_forum()
		super(TestApplicationClassForum, self).test_user_can_POST_new_forum_entry_header_only()

	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_user_can_POST_new_forum_entry_class_only(self):
		self._prepare_cs1313_forum()
		super(TestApplicationClassForum, self).test_user_can_POST_new_forum_entry_class_only()

	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_user_can_POST_new_forum_entry_mime_type_only(self):
		self._prepare_cs1313_forum()
		super(TestApplicationClassForum, self).test_user_can_POST_new_forum_entry_mime_type_only()

	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_user_can_POST_new_forum_entry_uncensored_by_default(self):
		self._prepare_cs1313_forum()
		super(TestApplicationClassForum, self).test_user_can_POST_new_forum_entry_uncensored_by_default()

	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_user_can_POST_new_forum_entry_and_search_for_it(self):
		self._prepare_cs1313_forum()
		super(TestApplicationClassForum, self).test_user_can_POST_new_forum_entry_and_search_for_it()

	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_user_can_POST_new_forum_entry_resulting_in_blog_being_sublocation(self):
		self._prepare_cs1313_forum()
		super(TestApplicationClassForum, self).test_user_can_POST_new_forum_entry_resulting_in_blog_being_sublocation()

	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_user_can_PUT_to_edit_existing_forum_topic_headline(self):
		self._prepare_cs1313_forum()
		super(TestApplicationClassForum, self).test_user_can_PUT_to_edit_existing_forum_topic_headline()

	@WithSharedApplicationMockDS(users=True, testapp=True)
	@time_monotonically_increases
	def test_creator_can_POST_new_comment(self):
		self._prepare_cs1313_forum()
		super(TestApplicationClassForum, self).test_creator_can_POST_new_comment()

	@WithSharedApplicationMockDS
	@time_monotonically_increases
	def test_contents_of_forum_can_be_sorted_by_comment_creation_date(self):
		self._prepare_cs1313_forum()
		super(TestApplicationClassForum, self).test_contents_of_forum_can_be_sorted_by_comment_creation_date()

	@WithSharedApplicationMockDS(users=True, testapp=True)
	@time_monotonically_increases
	def test_creator_can_POST_new_comment_to_contents(self):
		self._prepare_cs1313_forum()
		super(TestApplicationClassForum, self).test_creator_can_POST_new_comment_to_contents()

	@WithSharedApplicationMockDS(users=True, testapp=True)
	@time_monotonically_increases
	def test_creator_can_DELETE_comment_yielding_placeholders(self):
		self._prepare_cs1313_forum()
		super(TestApplicationClassForum, self).test_creator_can_DELETE_comment_yielding_placeholders()

	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_creator_can_DELETE_existing_empty_forum_topic(self):
		self._prepare_cs1313_forum()
		super(TestApplicationClassForum, self).test_creator_can_DELETE_existing_empty_forum_topic()

	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_creator_cannot_change_sharing_on__any_child(self):
		self._prepare_cs1313_forum()
		super(TestApplicationClassForum, self).test_creator_cannot_change_sharing_on__any_child()

	@WithSharedApplicationMockDS
	@time_monotonically_increases
	def test_creator_can_publish_topic_simple_visible_to_other_user_in_community(self):
		self._prepare_cs1313_forum()
		super(TestApplicationClassForum, self).test_creator_can_publish_topic_simple_visible_to_other_user_in_community()

	@WithSharedApplicationMockDS
	@time_monotonically_increases
	def test_published_topic_is_in_activity(self):
		self._prepare_cs1313_forum()
		super(TestApplicationClassForum, self).test_published_topic_is_in_activity()

	@WithSharedApplicationMockDS
	@time_monotonically_increases
	def test_published_topic_is_in_activity_until_DELETEd(self):
		self._prepare_cs1313_forum()
		super(TestApplicationClassForum, self).test_published_topic_is_in_activity_until_DELETEd()

	@WithSharedApplicationMockDS
	@time_monotonically_increases
	def test_community_user_can_comment_in_published_topic(self):
		self._prepare_cs1313_forum()
		super(TestApplicationClassForum, self).test_community_user_can_comment_in_published_topic()

	@WithSharedApplicationMockDS
	@time_monotonically_increases
	def test_community_user_can_favorite_topic(self):
		self._prepare_cs1313_forum()
		super(TestApplicationClassForum, self).test_community_user_can_favorite_topic()

	@WithSharedApplicationMockDS
	@time_monotonically_increases
	def test_community_user_can_edit_comment_in_published_topic(self):
		self._prepare_cs1313_forum()
		super(TestApplicationClassForum, self).test_community_user_can_edit_comment_in_published_topic()

	@WithSharedApplicationMockDS
	@time_monotonically_increases
	def test_community_user_comment_can_be_flagged(self):
		self._prepare_cs1313_forum()
		super(TestApplicationClassForum, self).test_community_user_comment_can_be_flagged()

	@WithSharedApplicationMockDS
	@time_monotonically_increases
	def test_community_user_can_search_for_published_topic(self):
		self._prepare_cs1313_forum()
		super(TestApplicationClassForum, self).test_community_user_can_search_for_published_topic()

	@WithSharedApplicationMockDS
	@time_monotonically_increases
	def test_community_user_can_search_for_publish_unpublished_comments(self):
		self._prepare_cs1313_forum()
		super(TestApplicationClassForum, self).test_community_user_can_search_for_publish_unpublished_comments()

	@WithSharedApplicationMockDS
	def test_post_canvas_image_in_headline_post_produces_fetchable_link(self):
		self._prepare_cs1313_forum()
		super(TestApplicationClassForum, self).test_post_canvas_image_in_headline_post_produces_fetchable_link()
