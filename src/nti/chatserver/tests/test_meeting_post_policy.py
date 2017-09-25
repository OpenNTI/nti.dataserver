#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import assert_that

from nti.testing.matchers import is_false
from nti.testing.matchers import validly_provides as verifiably_provides

import unittest

from nti.chatserver.interfaces import CHANNEL_DEFAULT

from nti.chatserver.interfaces import IMeetingPolicy

from nti.chatserver._meeting_post_policy import MessageTooBig
from nti.chatserver._meeting_post_policy import _ModeratedMeetingState
from nti.chatserver._meeting_post_policy import _MeetingMessagePostPolicy
from nti.chatserver._meeting_post_policy import _ModeratedMeetingMessagePostPolicy


class TestPolicy(unittest.TestCase):

    def test_provides(self):
        policy = _MeetingMessagePostPolicy()
        assert_that(policy, verifiably_provides(IMeetingPolicy))
        
        state = _ModeratedMeetingState()
        policy = _ModeratedMeetingMessagePostPolicy(moderation_state=state)
        assert_that(policy, verifiably_provides(IMeetingPolicy))

    def test_post_on_bad_channel(self):

        class O(object):
            channel = u"Not A Good Channel"

        assert_that(_MeetingMessagePostPolicy().post_message(O),
                    is_false())

        state = _ModeratedMeetingState()
        assert_that(_ModeratedMeetingMessagePostPolicy(moderation_state=state).post_message(O),
                    is_false())

    def test_post_too_big(self):

        class O(object):
            channel = CHANNEL_DEFAULT
            body = [u'abcd']

        policy = _MeetingMessagePostPolicy()
        policy.MAX_BODY_SIZE = 1

        with self.assertRaises(MessageTooBig):
            policy.post_message(O)
