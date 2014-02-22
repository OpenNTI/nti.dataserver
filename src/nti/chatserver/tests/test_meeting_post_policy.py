#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals

from hamcrest import assert_that
from nose.tools import assert_raises
from nti.chatserver import interfaces
from nti.testing.matchers import validly_provides as verifiably_provides, is_false

from nti.chatserver._meeting_post_policy import _MeetingMessagePostPolicy, _ModeratedMeetingMessagePostPolicy, _ModeratedMeetingState
from nti.chatserver._meeting_post_policy import MessageTooBig
import unittest

class TestPolicy(unittest.TestCase):
	def test_provides(self):

		policy = _MeetingMessagePostPolicy()
		assert_that( policy, verifiably_provides( interfaces.IMeetingPolicy ) )

		policy = _ModeratedMeetingMessagePostPolicy(moderation_state=_ModeratedMeetingState())
		assert_that( policy, verifiably_provides( interfaces.IMeetingPolicy ) )

	def test_post_on_bad_channel(self):
		class O(object):
			channel = "Not A Good Channel"

		assert_that( _MeetingMessagePostPolicy().post_message( O ),
					 is_false() )

		assert_that( _ModeratedMeetingMessagePostPolicy(moderation_state=_ModeratedMeetingState()).post_message( O ),
					 is_false() )

	def test_post_too_big(self):
		class O(object):
			channel = interfaces.CHANNEL_DEFAULT
			body = ['abcd']

		policy = _MeetingMessagePostPolicy()
		policy.MAX_BODY_SIZE = 1

		with assert_raises(MessageTooBig):
			policy.post_message( O )
