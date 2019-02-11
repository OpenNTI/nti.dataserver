#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from Queue import Queue

import fudge
from hamcrest import assert_that, is_, is_not, has_length
from zope import interface, lifecycleevent
from zope.component import subscribers
from zope.event import notify
from zope.intid import IntIdAddedEvent
from zope.location.interfaces import IRoot

from nti.dataserver.contenttypes.forums.forum import CommunityForum, Forum
from nti.dataserver.contenttypes.forums.interfaces import ICommunityBoard, IHeadlineTopic, \
    ISendEmailOnForumTypeCreation, IForumTypeCreatedNotificationUsers
from nti.dataserver.contenttypes.forums.post import Post, HeadlinePost, GeneralHeadlinePost
from nti.dataserver.contenttypes.forums.subscribers import _send_email_on_forum_type_creation
from nti.dataserver.contenttypes.forums.tests import ForumLayerTest
from nti.dataserver.contenttypes.forums.topic import CommunityHeadlineTopic, Topic

from nti.dataserver.tests.mock_dataserver import WithMockDS, WithMockDSTrans, DataserverLayerTest
from nti.dataserver.users import Community, User

__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


class TestJob(DataserverLayerTest):

    set_up_packages = ('nti.dataserver', 'nti.dataserver.contenttypes.forums')

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
        post = GeneralHeadlinePost()
        post.body = [u'<html><body>a headline post about important things</body></html>']
        topic.headline = post

        forum[topic_name] = topic
        return topic

    @fudge.patch('nti.asynchronous.scheduled.utils.get_scheduled_queue')
    @fudge.patch('nti.dataserver.contenttypes.forum.job.send_creation_notification_email')
    @WithMockDSTrans
    def test_creation_email(self, fake_queue, fake_email):
        queue = self._setup_mock_email_job(fake_queue)
        fake_email.is_callable()
        forum = self._create_community_forum(forum_name=u'test_forum')
        interface.alsoProvides(forum, ISendEmailOnForumTypeCreation)
        topic = self._add_community_topic(forum=forum, topic_name=u'test_topic')
        from IPython.terminal.debugger import set_trace;set_trace()
        event = IntIdAddedEvent(object=topic, event=None)
        notify(event)
        _send_email_on_forum_type_creation(topic, None)
        assert_that(queue.empty(), is_not(True))
