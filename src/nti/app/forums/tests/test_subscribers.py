#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from hamcrest import assert_that
from hamcrest import has_length
from hamcrest import is_

from zope import lifecycleevent

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.contentfragments.interfaces import PlainTextContentFragment

from nti.dataserver.contenttypes.forums.interfaces import ICommunityBoard

from nti.dataserver.contenttypes.forums.post import CommunityHeadlinePost
from nti.dataserver.contenttypes.forums.post import GeneralForumComment

from nti.dataserver.contenttypes.forums.topic import CommunityHeadlineTopic

from nti.dataserver.tests import mock_dataserver

from nti.dataserver.users import User


class TestSubscribers(ApplicationLayerTest):

    default_community = 'test_comm'

    @staticmethod
    def _get_forum(community_name, forum_name=u'Forum'):
        community = User.get_entity(community_name)
        board = ICommunityBoard(community)
        return board[forum_name]

    @staticmethod
    def _add_community_topic(creator, forum, topic_name):
        topic = CommunityHeadlineTopic()
        topic.title = u'a test'
        topic.creator = creator

        forum[topic_name] = topic

        return topic

    @staticmethod
    def _add_comment(creator,
                     topic,
                     request=None,
                     mentions=()):
        comment = GeneralForumComment()
        comment.creator = creator
        comment.mentions = mentions

        if request is not None:
            request.remote_user = creator
            request.context = comment

        topic[topic.generateId(prefix=u'comment')] = comment
        return comment

    @WithSharedApplicationMockDS(users=('topic_owner', 'comment_user'),
                                 testapp=False,
                                 default_authenticate=False)
    def test_reply_notification_if_mentioned(self):
        with mock_dataserver.mock_db_trans():
            user2 = self.users[u'topic_owner']
            user3 = self.users[u'comment_user']
            forum = self._get_forum('test_comm')

            topic = self._add_community_topic(user2, forum, u'Hello')
            topic.publish()

            # Top comment
            self._add_comment(user3, topic)
            assert_that(user2.notificationCount.value, is_(1))

            # Don't send if the topic author is mentioned, as we
            # currently prefer that notification
            mentions = PlainTextContentFragment(user2.username),
            self._add_comment(user3, topic, mentions=mentions)
            assert_that(user2.notificationCount.value, is_(1))

    @staticmethod
    def _add_community_post(topic, post):
        post.__parent__ = topic
        post.creator = topic.creator
        topic.headline = post
        return post

    @WithSharedApplicationMockDS(users=("leeroy.jenkins",),
                                 testapp=False,
                                 default_authenticate=False)
    def test_topic_mentions_updated(self):
        with mock_dataserver.mock_db_trans():
            topic_owner = self._create_user('topic_owner')
            forum = self._get_forum('test_comm')
            topic = self._add_community_topic(topic_owner,
                                              forum=forum,
                                              topic_name=u'test_topic')
            post = self._add_community_post(topic, CommunityHeadlinePost())
            assert_that(topic.mentions, has_length(0))

            post.mentions = (PlainTextContentFragment("leeroy.jenkins"),)
            lifecycleevent.modified(post)
            assert_that(topic.mentions, is_(post.mentions))
