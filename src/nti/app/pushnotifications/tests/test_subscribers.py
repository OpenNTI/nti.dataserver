#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

import fudge

from hamcrest import is_
from hamcrest import none
from hamcrest import has_entries
from hamcrest import has_length
from hamcrest import is_not
from hamcrest import not_none
from hamcrest import assert_that
from hamcrest import same_instance

from zope import component

from nti.app.testing.decorators import WithSharedApplicationMockDS
from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.dataserver.users import Community

from nti.dataserver.contenttypes.forums.forum import CommunityForum
from nti.dataserver.contenttypes.forums.interfaces import ICommunityBoard
from nti.dataserver.contenttypes.forums.post import GeneralForumComment
from nti.dataserver.contenttypes.forums.topic import CommunityHeadlineTopic

from nti.dataserver.tests import mock_dataserver

class TestSubscribers(ApplicationLayerTest):

	def _add_comment(self, creator, topic, inReplyTo=None):
		comment = GeneralForumComment()
		comment.creator = creator
		if inReplyTo:
			comment.inReplyTo = inReplyTo
		topic[topic.generateId(prefix=u'comment')] = comment
		return comment

	@WithSharedApplicationMockDS(users=False, testapp=True, default_authenticate=False)
	@fudge.patch("nti.app.pushnotifications.subscribers._mailer",
				 "nti.app.pushnotifications.subscribers._is_subscribed")
	def test_threadable_added(self, mock_mailer, mock_is_subscribed):
		class _MockMailer(object):
			_calls = []
			def queue_simple_html_text_email(self, template_name, subject, recipients, template_args, reply_to, package, text_template_extension):
				self._calls.append((template_name, subject, recipients, reply_to, text_template_extension, template_args))

			def reset(self):
				del self._calls[:]

		_mockMailer = _MockMailer()
		mock_mailer.is_callable().returns(_mockMailer)
		mock_is_subscribed.is_callable().returns(True)

		with mock_dataserver.mock_db_trans(self.ds):
			community = Community.create_community(self.ds, username=u"test_demo")
			user1 = self._create_user(username=u'forum_owner', external_value={'email': u'forum_owner@example.com'})
			user2 = self._create_user(username=u'topic_owner', external_value={'email': u'topic_owner@example.com'})
			user3 = self._create_user(username=u'comment_user1', external_value={'email': u'comment_user1@example.com'})
			user4 = self._create_user(username=u'comment_user2', external_value={'email': u'comment_user2@example.com'})
			user5 = self._create_user(username=u"comment_user3")
			for _user in (user1, user2, user3, user4, user5):
				_user.record_dynamic_membership(community)

			board = ICommunityBoard(community)

			forum = CommunityForum()
			forum.title = u'test'
			forum.creator = user1
			board[u'Forum'] = forum

			topic = CommunityHeadlineTopic()
			topic.title = u'a test'
			topic.creator = user2
			forum[u'Hello'] = topic
			topic.publish()


			# Top comment
			comment1 = self._add_comment(user3, topic, inReplyTo=None)
			assert_that(_mockMailer._calls, has_length(0))

			# Same creator with the creator of inReplyTo
			comment2 = self._add_comment(user3, topic, inReplyTo=comment1)
			assert_that(_mockMailer._calls, has_length(0))

			mock_is_subscribed.is_callable().returns(False)
			comment3 = self._add_comment(user4, topic, inReplyTo=comment1)
			assert_that(_mockMailer._calls, has_length(0))

			mock_is_subscribed.is_callable().returns(None)
			comment4 = self._add_comment(user4, topic, inReplyTo=comment1)
			assert_that(_mockMailer._calls, has_length(0))

			# Success
			mock_is_subscribed.is_callable().returns(True)
			comment5 = self._add_comment(user4, topic, inReplyTo=comment1)
			assert_that(_mockMailer._calls, has_length(1))
			assert_that(_mockMailer._calls[0][0], is_('nti.app.pushnotifications:templates/digest_email'))
			assert_that(_mockMailer._calls[0][1], is_('Your NextThought Updates'))
			assert_that(_mockMailer._calls[0][2], is_(['comment_user1@example.com']))
			assert_that(_mockMailer._calls[0][3], is_(None))
			assert_that(_mockMailer._calls[0][4], is_('.mak'))
			assert_that(_mockMailer._calls[0][5], has_entries({ 'total_found': 1,
																'first_name': 'comment_user1',
																'site_name': 'Example',
																'notable_text': 'A user has replied to one of your comments.',
																'email_to': 'comment_user1@example.com (comment_user1)'}))

			comment6 = self._add_comment(user3, topic, inReplyTo=comment3)
			assert_that(_mockMailer._calls, has_length(2))
			assert_that(_mockMailer._calls[1][2], is_(['comment_user2@example.com']))
			assert_that(_mockMailer._calls[1][5], has_entries({ 'total_found': 1,
																'first_name': 'comment_user2',
																'site_name': 'Example',
																'notable_text': 'A user has replied to one of your comments.',
																'email_to': 'comment_user2@example.com (comment_user2)'}))

			_mockMailer.reset()

			# Top comment other
			comment11 = self._add_comment(user5, topic, inReplyTo=None)
			assert_that(_mockMailer._calls, has_length(0))

			# No email found for the top comment
			comment12 = self._add_comment(user4, topic, inReplyTo=comment11)
			assert_that(_mockMailer._calls, has_length(0))
