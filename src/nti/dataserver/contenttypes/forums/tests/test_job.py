#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from Queue import Queue

import fudge

from hamcrest import assert_that
from hamcrest import is_
from hamcrest import is_not

from pyramid.testing import DummyRequest

from zope import interface

from nti.contentfile.model import ContentBlobFile

from nti.dataserver.contenttypes import Canvas

from nti.dataserver.contenttypes.forums.forum import CommunityForum

from nti.dataserver.contenttypes.forums.interfaces import ICommunityBoard
from nti.dataserver.contenttypes.forums.interfaces import ISendEmailOnForumTypeCreation

from nti.dataserver.contenttypes.forums.post import GeneralHeadlinePost

from nti.dataserver.contenttypes.forums.subscribers import _send_email_on_forum_type_creation

from nti.dataserver.contenttypes.forums.topic import CommunityHeadlineTopic

from nti.dataserver.tests.mock_dataserver import DataserverLayerTest
from nti.dataserver.tests.mock_dataserver import WithMockDSTrans

from nti.dataserver.users import Community
from nti.dataserver.users import User

from nti.mailer.interfaces import IEmailAddressable

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

    def _add_community_topic(self, forum, topic_name, creator):
        topic = CommunityHeadlineTopic()
        topic.title = u'a test'
        topic.creator = creator
        forum[topic_name] = topic
        return topic

    @fudge.patch('nti.dataserver.contenttypes.forums.job.get_current_request')
    @fudge.patch('nti.asynchronous.scheduled.utils.get_scheduled_queue')
    @fudge.patch('nti.dataserver.contenttypes.forums.job.send_creation_notification_email')
    @WithMockDSTrans
    def test_creation_email(self, fake_request, fake_queue, fake_email):
        fake_request.is_callable().returns(DummyRequest())
        queue = self._setup_mock_email_job(fake_queue)
        fake_kwargs = {}

        def stub(**kwargs):
            fake_kwargs.update(**kwargs)
        fake_email.is_callable().calls(stub)

        forum = self._create_community_forum(forum_name=u'test_forum')
        interface.alsoProvides(forum, ISendEmailOnForumTypeCreation)
        sj = User.get_user(u'sjohnson@nextthought.com')
        topic = self._add_community_topic(forum=forum, topic_name=u'test_topic', creator=sj)
        post = GeneralHeadlinePost()
        body = [u'<html><body>a headline post about important things</body></html>']
        post.body = body
        topic.headline = post
        _send_email_on_forum_type_creation(topic, None)
        assert_that(queue.empty(), is_not(True))

        # give super user an email address
        addressable = IEmailAddressable(sj)
        addressable.email = u'sjohnson@nextthought.com'

        # execute the job
        job = queue.get()
        job()

        assert_that(fake_kwargs['subject'], is_(u'Discussion a test created in test'))
        assert_that(fake_kwargs['message'], is_('a headline post about important things'))

        body.append(u'abc')
        body.append(u'xyz')
        post.body = body

        _send_email_on_forum_type_creation(topic, None)
        assert_that(queue.empty(), is_not(True))

        # execute the job
        job = queue.get()
        job()

        assert_that(fake_kwargs['subject'], is_(u'Discussion a test created in test'))
        assert_that(fake_kwargs['message'], is_('a headline post about important things'
                                                ' abc'
                                                ' xyz'))

        body.append(ContentBlobFile())
        body.append(Canvas())
        post.body = body

        _send_email_on_forum_type_creation(topic, None)
        assert_that(queue.empty(), is_not(True))

        # execute the job
        job = queue.get()
        job()

        assert_that(fake_kwargs['subject'], is_(u'Discussion a test created in test'))
        assert_that(fake_kwargs['message'], is_('a headline post about important things'
                                                ' abc'
                                                ' xyz'))
