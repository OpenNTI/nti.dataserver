#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import fudge

from hamcrest import assert_that
from hamcrest import has_length
from hamcrest import is_
from hamcrest import is_not

from Queue import Queue

from zope import interface

from zope.component import subscribers

from zope.location.interfaces import IRoot

from nti.app.testing.request_response import DummyRequest

from nti.dataserver.contenttypes.forums.forum import CommunityForum
from nti.dataserver.contenttypes.forums.forum import Forum

from nti.dataserver.contenttypes.forums.interfaces import ICommunityBoard
from nti.dataserver.contenttypes.forums.interfaces import IForumTypeCreatedNotificationUsers
from nti.dataserver.contenttypes.forums.interfaces import IHeadlineTopic
from nti.dataserver.contenttypes.forums.interfaces import ISendEmailOnForumTypeCreation

from nti.dataserver.contenttypes.forums.subscribers import _send_email_on_forum_type_creation

from nti.dataserver.contenttypes.forums.topic import CommunityHeadlineTopic
from nti.dataserver.contenttypes.forums.topic import Topic

from nti.dataserver.tests.mock_dataserver import DataserverLayerTest
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.dataserver.users import Community
from nti.dataserver.users import User

__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


class TestSubscribers(DataserverLayerTest):

    def _setup_mock_email_job(self, fake_queue):
        queue = Queue()
        fake_queue.is_callable().returns(queue)
        assert_that(queue.empty(), is_(True))
        return queue

    def _create_community_forum(self, forum_name):
        comm = Community.create_community(self.ds, username="CHEM4970.ou.nextthought.com")

        sj = User.create_user(self.ds,
                              username=u'sjohnson@nextthought.com',
                              external_value={'realname': u'Steve Johnson',
                                              'email': u'sjohnson@nextthought.com'})
        sj.record_dynamic_membership(comm)
        sj.follow(comm)

        board = ICommunityBoard(comm)

        forum = CommunityForum()
        forum.title = u'test'

        board[forum_name] = forum

        return forum

    def _add_community_topic(self, forum, topic_name):
        topic = CommunityHeadlineTopic()
        topic.title = u'a test'
        topic.creator = u'sjohnson@nextthought.com'

        forum[topic_name] = topic
        return topic

    @fudge.patch('nti.dataserver.contenttypes.forums.job.get_current_request')
    @fudge.patch('nti.dataserver.job.email.to_external_ntiid_oid')
    @fudge.patch('nti.asynchronous.scheduled.utils.get_scheduled_queue')
    @WithMockDSTrans
    def test_topic_creation_email_subscriber(self, fake_request, fake_ntiid, fake_queue):
        fake_request.is_callable().returns(DummyRequest())
        fake_ntiid.is_callable().returns('some:ntiid')
        queue = self._setup_mock_email_job(fake_queue)
        forum = Forum()
        interface.alsoProvides(forum, IRoot)  # Mock this in for the purpose of testing
        topic = Topic()
        topic.__parent__ = forum
        interface.alsoProvides(topic, IHeadlineTopic)
        # Assert we dont send email if parent does not provide iface
        _send_email_on_forum_type_creation(topic, None)
        assert_that(queue.empty(), is_(True))

        # Assert we send email if parent provides iface
        interface.alsoProvides(forum, ISendEmailOnForumTypeCreation)
        _send_email_on_forum_type_creation(topic, None)
        assert_that(queue.empty(), is_not(True))

    @WithMockDSTrans
    def test_community_users_for_topic_type(self):
        forum = self._create_community_forum(forum_name=u'test_forum')
        topic = self._add_community_topic(forum=forum, topic_name=u'test_topic')
        usernames = set()
        for subscriber in subscribers((topic,), IForumTypeCreatedNotificationUsers):
            usernames = usernames.union(subscriber.get_usernames())
        assert_that(usernames, has_length(1))
