#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import fudge

from hamcrest import assert_that
from hamcrest import is_
from hamcrest import is_not

from Queue import Queue

from zope import interface

from zope.location.interfaces import IRoot

from nti.dataserver.contenttypes.forums.board import Board

from nti.dataserver.contenttypes.forums.forum import Forum

from nti.dataserver.contenttypes.forums.interfaces import ISendEmailOnForumTypeCreation

from nti.dataserver.contenttypes.forums.subscribers import _send_email_on_forum_type_creation

from nti.dataserver.contenttypes.forums.tests import ForumLayerTest

from nti.dataserver.contenttypes.forums.topic import Topic

__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)


class TestSubscribers(ForumLayerTest):

    def _setup_mock_email_job(self, fake_queue):
        queue = Queue()
        fake_queue.is_callable().returns(queue)
        assert_that(queue.empty(), is_(True))
        return queue

    @fudge.patch('nti.asynchronous.scheduled.utils.get_scheduled_queue')
    def test_topic_creation_email_subscriber(self, fake_queue):
        queue = self._setup_mock_email_job(fake_queue)
        forum = Forum()
        interface.alsoProvides(forum, IRoot)  # Mock this in for the purpose of testing
        topic = Topic()
        topic.__parent__ = forum

        # Assert we dont send email if parent does not provide iface
        _send_email_on_forum_type_creation(topic, None)
        assert_that(queue.empty(), is_(True))

        # Assert we send email if parent provides iface
        interface.alsoProvides(forum, ISendEmailOnForumTypeCreation)
        _send_email_on_forum_type_creation(topic, None)
        assert_that(queue.empty(), is_not(True))

    @fudge.patch('nti.asynchronous.scheduled.utils.get_scheduled_queue')
    def test_forum_creation_email_subscriber(self, fake_queue):
        queue = self._setup_mock_email_job(fake_queue)
        board = Board()
        interface.alsoProvides(board, IRoot)  # Mock this in for the purpose of testing
        forum = Forum()
        forum.__parent__ = board

        # Assert we dont send email if parent does not provide iface
        _send_email_on_forum_type_creation(forum, None)
        assert_that(queue.empty(), is_(True))

        # Assert we send email if parent provides iface
        interface.alsoProvides(board, ISendEmailOnForumTypeCreation)
        _send_email_on_forum_type_creation(forum, None)
        assert_that(queue.empty(), is_not(True))
