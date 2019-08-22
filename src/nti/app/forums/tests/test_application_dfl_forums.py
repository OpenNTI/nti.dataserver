#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_
from hamcrest import has_item
from hamcrest import has_entry
from hamcrest import has_length
from hamcrest import assert_that
from hamcrest import has_entries
from hamcrest import has_property
from hamcrest import greater_than_or_equal_to

from zope import component

from zope.component import eventtesting

from zope.lifecycleevent import IObjectRemovedEvent

from zope.intid.interfaces import IIntIds
from zope.intid.interfaces import IIntIdRemovedEvent

from nti.dataserver.users.friends_lists import DynamicFriendsList

from nti.dataserver.contenttypes.forums.forum import DEFAULT_FORUM_NAME

from nti.dataserver.contenttypes.forums.board import DFLBoard
from nti.dataserver.contenttypes.forums.forum import DFLForum
from nti.dataserver.contenttypes.forums.topic import DFLHeadlineTopic

from nti.app.testing.webtest import TestApp as _TestApp
from nti.app.testing.application_webtest import ApplicationLayerTest
from nti.app.testing.decorators import WithSharedApplicationMockDSHandleChanges as WithSharedApplicationMockDS

from nti.app.forums.tests.base_forum_testing import _plain
from nti.app.forums.tests.base_forum_testing import AbstractPostCreationMixin

from nti.dataserver.tests import mock_dataserver

from nti.testing.time import time_monotonically_increases

_FORUM_NAME = DEFAULT_FORUM_NAME
_BOARD_NAME = DFLBoard.__default_name__

class TestApplicationDFLorums(ApplicationLayerTest, AbstractPostCreationMixin):

	__test__ = True

	extra_environ_default_user = 'original_user@foo'

	default_entityname = None
	forum_url_relative_to_user = _BOARD_NAME + '/' + _FORUM_NAME

	board_ntiid = None
	board_content_type = None
	board_ntiid_checker = None
	board_link_rel = forum_link_rel = _BOARD_NAME

	forum_type = DFLForum
	forum_title = _FORUM_NAME
	forum_topic_content_type = None
	forum_headline_class_type = 'Post'
	forum_content_type = 'application/vnd.nextthought.forums.dflforum+json'

	forum_ntiid = None
	forum_topic_ntiid_base = None

	forum_topic_comment_content_type = 'application/vnd.nextthought.forums.generalforumcomment+json'

	def _user_dfl_fixture(self):

		with mock_dataserver.mock_db_trans(self.ds):
			user = self._create_user(username='ichigo@bleach')
			user2 = self._create_user(username='aizen@bleach')
			user3 = self._create_user(username='rukia@bleach')
			user4 = self._create_user(username='zaraki@bleach')

			bleach = DynamicFriendsList(username='Bleach')
			bleach.creator = user  # Creator must be set
			user.addContainedObject(bleach)
			bleach.addFriend(user2)
			bleach.addFriend(user3)

			self.user_username = user.username
			self.user2_username = user2.username
			self.user3_username = user3.username
			self.user4_username = user4.username

			self.default_entityname = self.dfl_name = bleach.NTIID
			intids = component.getUtility(IIntIds)
			uid = intids.getId(bleach)

			self.forum_ntiid = 'tag:nextthought.com,2011-10:%s-Forum:GeneralDFL-Forum' % uid
			self.forum_topic_ntiid_base = 'tag:nextthought.com,2011-10:%s-Topic:GeneralDFL-Forum.' % uid

			self.board_ntiid = 'tag:nextthought.com,2011-10:%s-Board:GeneralDFL-DiscussionBoard' % uid
			self.board_ntiid_checker = self.board_ntiid

			self.board_pretty_url = "/dataserver2/users/ichigo@bleach/FriendsLists/Bleach/DiscussionBoard"
			self.forum_pretty_url = '/dataserver2/users/ichigo@bleach/FriendsLists/Bleach/' + self.forum_url_relative_to_user

		self.testapp = _TestApp(self.app, extra_environ=self._make_extra_environ(username=self.user_username))
		self.testapp2 = _TestApp(self.app, extra_environ=self._make_extra_environ(username=self.user2_username))
		self.testapp3 = _TestApp(self.app, extra_environ=self._make_extra_environ(username=self.user3_username))
		self.testapp4 = _TestApp(self.app, extra_environ=self._make_extra_environ(username=self.user4_username))

	def setUp(self):
		super(TestApplicationDFLorums, self).setUp()
		self.board_content_type = DFLBoard.mimeType + '+json'
		self.forum_topic_content_type = DFLHeadlineTopic.mimeType + '+json'

	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_default_board_in_links(self):
		self._user_dfl_fixture()
		entity = self.resolve_user(username=self.default_entityname)
		href = self.require_link_href_with_rel(entity, self.board_link_rel)
		assert_that(href, is_(self.board_pretty_url))

	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_default_board_can_be_resolved_by_ntiid(self):
		self._user_dfl_fixture()
		board_res = self.fetch_by_ntiid(self.board_ntiid)
		assert_that(board_res.json_body, has_entry('NTIID', self.board_ntiid))
		assert_that(board_res, has_property('content_type', self.board_content_type))
		assert_that(board_res.json_body, has_entry('MimeType', _plain(self.board_content_type)))
		self.require_link_href_with_rel(board_res.json_body, 'contents')

	@WithSharedApplicationMockDS(users=('sjohnson@nextthought.com',), testapp=True, default_authenticate=True)
	@time_monotonically_increases
	def test_super_user_can_edit_forum_description(self):
		self._user_dfl_fixture()
		# relying on @nextthought.com automatically being an admin
		adminapp = _TestApp(self.app,
							 extra_environ=self._make_extra_environ(username='sjohnson@nextthought.com'))
		forum_data = self._create_post_data_for_POST()
		forum_res = adminapp.post_json(self.board_pretty_url, forum_data, status=201)

		board_res = adminapp.get(self.board_pretty_url)
		board_contents = self.require_link_href_with_rel(board_res.json_body, 'contents')
		board_contents_res = adminapp.get(board_contents)

		adminapp.put_json(forum_res.location, {'description': 'The updated description'})

		forum_res = self.testapp.get(forum_res.location)
		assert_that(forum_res.json_body, has_entry('description', "The updated description"))

		# And when we get the board again, it shows up as changed
		adminapp.get(board_contents,
					 headers={b'If-None-Match': board_contents_res.etag,
							b'If-Modified-Since': board_contents_res.headers['Last-Modified']},
					 status=200)

	@WithSharedApplicationMockDS(users=('sjohnson@nextthought.com',), testapp=True, default_authenticate=True)
	def test_super_user_can_edit_forum_description_using_field(self):
		# relying on @nextthought.com automatically being an admin
		self._user_dfl_fixture()
		adminapp = _TestApp(self.app, extra_environ=self._make_extra_environ(username='sjohnson@nextthought.com'))
		forum_data = self._create_post_data_for_POST()
		forum_res = adminapp.post_json(self.board_pretty_url, forum_data, status=201)

		adminapp.put_json(forum_res.location + '++fields++description', 'The updated description')

		forum_res = self.testapp.get(forum_res.location)
		assert_that(forum_res.json_body, has_entry('description', "The updated description"))

	@WithSharedApplicationMockDS(users=('sjohnson@nextthought.com',), testapp=True, default_authenticate=True)
	def test_super_user_can_delete_forum(self):
		# relying on @nextthought.com automatically being an admin
		self._user_dfl_fixture()
		adminapp = _TestApp(self.app, extra_environ=self._make_extra_environ(username='sjohnson@nextthought.com'))
		forum_data = self._create_post_data_for_POST()
		forum_res = adminapp.post_json(self.board_pretty_url, forum_data, status=201)

		# Normal user (non member) cannot delete
		self.testapp4.delete(forum_res.location, status=403)

		# admin can
		eventtesting.clearEvents()
		adminapp.delete(forum_res.location, status=204)

		rem_events = eventtesting.getEvents(IObjectRemovedEvent)
		assert_that(rem_events, has_length(1))
		self.testapp.get(forum_res.location, status=404)

	@WithSharedApplicationMockDS(users=('sjohnson@nextthought.com',), testapp=True, default_authenticate=True)
	def test_super_user_can_delete_forum_with_topic_and_comments(self):
		# relying on @nextthought.com automatically being an admin
		self._user_dfl_fixture()
		adminapp = _TestApp(self.app, extra_environ=self._make_extra_environ(username='sjohnson@nextthought.com'))
		forum_data = self._create_post_data_for_POST()
		forum_res = adminapp.post_json(self.board_pretty_url, forum_data, status=201)

		# now community user publishes
		publish_res, _ = self._POST_and_publish_topic_entry(forum_url=forum_res.location)

		# and for grins, community user comments on own topic
		comment_res = self.testapp.post_json(publish_res.json_body['href'], self._create_comment_data_for_POST())

		# now the admin can delete the forum, destroying the forum,
		# the topic, the headline post, and the comment
		eventtesting.clearEvents()
		adminapp.delete(forum_res.location, status=204)
		# There's only one ObjectRemovedEvent, but it is dispatched
		# to all the sublocations
		rem_events = eventtesting.getEvents(IObjectRemovedEvent)
		assert_that(rem_events, has_length(1))

		# So all four of the objects got their intid removed
		int_rem_events = eventtesting.getEvents(IIntIdRemovedEvent)
		assert_that(int_rem_events, has_length(4))
		# So all the locations 404
		for res in forum_res, publish_res, comment_res:
			self.testapp.get(res.location, status=404)
		# and nothing is searchable
		for term in self.forum_comment_unique, self.forum_headline_unique:
			self.search_user_rugd(term, username=self.user4_username, status=403)

	@WithSharedApplicationMockDS(users=('sjohnson@nextthought.com',), testapp=True, default_authenticate=True)
	def test_creator_can_DELETE_DFL_user_comment_in_published_topic(self):
		self._user_dfl_fixture()

		publish_res, _ = self._POST_and_publish_topic_entry()
		topic_url = publish_res.location

		# non-creator comment
		comment_data = self._create_comment_data_for_POST()
		comment_res = self.testapp2.post_json(topic_url, comment_data, status=201)
		edit_href = self.require_link_href_with_rel(comment_res.json_body, 'edit')

		self.testapp3.delete(edit_href, status=403)  # forbidden by ACL

		# can be deleted by creator
		self.testapp.delete(edit_href, status=204)

	@WithSharedApplicationMockDS
	def test_dfl_topics_and_comments_in_RUGD_and_RSTREAM(self):
		self._user_dfl_fixture()

		testapp = self.testapp
		testapp2 = self.testapp2

		publish_res, _ = self._POST_and_publish_topic_entry()
		topic_url = publish_res.location

		# The creator of the dfl topic doesn't see it in his RUGD
		# without applying some filters
		self.fetch_user_root_rugd(testapp, self.user_username, status=404)

		res = self.fetch_user_root_rugd(testapp, self.user_username,
 										params={'filter': 'MeOnly',
 												'accept': 'application/vnd.nextthought.forums.dflheadlinetopic'})
		assert_that(res.json_body, has_entry('FilteredTotalItemCount', 1))
		assert_that(res.json_body, has_entry('TotalItemCount', greater_than_or_equal_to(3)))  # Both topic and comment
		assert_that(res.json_body['Items'], has_item(has_entry('title', publish_res.json_body['title'])))

		# Now, the non-creator has the topic in his stream as created
		res = self.fetch_user_root_rstream(testapp2, self.user2_username)
		assert_that(res.json_body, has_entry('TotalItemCount', 2))
		assert_that(res.json_body['Items'][0], has_entry('ChangeType', 'Shared'))
		created_event_time = res.json_body['Items'][0]['Last Modified']

		# non-creator adds comment
		comment_data = self._create_comment_data_for_POST()
		testapp2.post_json(topic_url, comment_data, status=201)

		# the creator gets the comment, but not the topic in his stream (because he created it)
		res = self.fetch_user_root_rstream(testapp, self.user_username)
		assert_that(res.json_body, has_entry('TotalItemCount', 1))
		assert_that(res.json_body['Items'][0], has_entry('ChangeType', 'Created'))

		# For the commenter, the comment did not change the event in the stream for the topic, it stays
		# exactly the same
		res = self.fetch_user_root_rstream(testapp2, self.user2_username)  # , status=404 )
		assert_that(res.json_body, has_entry('TotalItemCount', 2))
		assert_that(res.json_body['Items'][0], has_entries('ChangeType', 'Shared',
 															'Last Modified', created_event_time))

		# The creator of the topic never sees it in his RUGD, not
		# even after a comment is added
		self.fetch_user_root_rugd(testapp, self.user_username, status=404)

		# The commentor also has neither the topic he didn't create,
		# nor the comment he did create, in his RUGD, without applying filters
		self.fetch_user_root_rugd(testapp2, self.user2_username, status=404)

		res = self.fetch_user_root_rugd(testapp2, self.user2_username, params={'filter': 'MeOnly'})
		assert_that(res.json_body, has_entry('TotalItemCount', 1))

	@WithSharedApplicationMockDS(users=True, testapp=True)
	def test_creator_cannot_change_sharing_on_dfl_topic(self):
		self._user_dfl_fixture()
		testapp = self.testapp
		res = self._POST_topic_entry()

		topic_url = res.location
		self.require_link_href_with_rel(res.json_body['headline'], 'edit')

		eventtesting.clearEvents()

		# Field updates
		# Cannot change the entry
		testapp.put_json(topic_url + '/++fields++sharedWith',
 						 ['Everyone'],
 						 # Because of the way traversal is right now, this results in a 404,
 						 # when really we want a 403
 						 status=404)

		# Nor when putting the whole thing
		# The entry itself simply cannot be modified (predicate mismatch right now)
		testapp.put_json(topic_url,
 						 {'sharedWith': ['Everyone']},
 						 status=403)

	@WithSharedApplicationMockDS
	@time_monotonically_increases
	def test_contents_of_forum_last_modified_changes_when_new_topic_added_published(self):
		self._user_dfl_fixture()

		self._POST_and_publish_topic_entry()
		forum_res = self.testapp.get(self.forum_pretty_url)
		forum_contents_href = self.require_link_href_with_rel(forum_res.json_body, 'contents')

		forum_contents_res = self.testapp.get(forum_contents_href)
		assert_that(forum_contents_res.json_body, has_entry('TotalItemCount', 1))

		self._POST_and_publish_topic_entry()  # create a second one

		forum_contents_res2 = self.testapp.get(	forum_contents_href,
 												headers={b'If-None-Match': forum_contents_res.etag,
 														 b'If-Modified-Since': forum_contents_res.headers['Last-Modified']},
 												status=200)

		assert_that(forum_contents_res2.json_body, has_entry('TotalItemCount', 2))

		forum_contents_res3 = self.testapp.get(	forum_contents_href,
 												params={b'searchTerm': 'notfound'},
 												status=200)

		assert_that(forum_contents_res3.json_body, has_entry('FilteredTotalItemCount', 0))

		forum_contents_res3 = self.testapp.get(	forum_contents_href,
 												params={b'searchTerm': 'blog'},
 												status=200)

		assert_that(forum_contents_res3.json_body, has_entry(u'TotalItemCount', 2))

	@WithSharedApplicationMockDS
	@time_monotonically_increases
	def test_contents_of_forum_last_modified_changes_when_new_topic_title_changed(self):
		self._user_dfl_fixture()

		topic_res, _ = self._POST_and_publish_topic_entry()
		forum_res = self.testapp.get(self.forum_pretty_url)
		forum_contents_href = self.require_link_href_with_rel(forum_res.json_body, 'contents')

		forum_contents_res = self.testapp.get(forum_contents_href)
		assert_that(forum_contents_res.json_body, has_entry('TotalItemCount', 1))

		self.testapp.put_json(topic_res.json_body['headline']['href'], {'title': "A new and different title"})

		self.testapp.get(forum_contents_href,
 						 headers={b'If-None-Match': forum_contents_res.etag,
 							   	  b'If-Modified-Since': forum_contents_res.headers['Last-Modified']},
 						 status=200)
	@WithSharedApplicationMockDS
	@time_monotonically_increases
	def test_contents_of_board_last_modified_changes_when_new_topic_added_to_forum(self):
		self._user_dfl_fixture()

		board_pretty_url = self.board_pretty_url

		self._POST_and_publish_topic_entry()
		board_res = self.testapp.get( board_pretty_url )
		board_contents_href = self.require_link_href_with_rel( board_res.json_body, 'contents' )

		board_contents_res = self.testapp.get( board_contents_href )
		assert_that( board_contents_res.json_body, has_entry( 'TotalItemCount', 1 ) )

		self._POST_and_publish_topic_entry() # create a second one

		board_contents_res2 = self.testapp.get(	board_contents_href,
 												headers={b'If-None-Match': board_contents_res.etag,
 														  b'If-Modified-Since': board_contents_res.headers['Last-Modified']},
 												status=200)

		assert_that( board_contents_res2.json_body, has_entry( 'TotalItemCount', 1 ) )
