#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
$Id$
"""
from __future__ import print_function, unicode_literals

from hamcrest import assert_that

from nti.chatserver import interfaces
from nti.tests import verifiably_provides, is_false

from nti.chatserver._meeting_post_policy import _MeetingMessagePostPolicy, _ModeratedMeetingMessagePostPolicy, _ModeratedMeetingState

def test_provides():

	policy = _MeetingMessagePostPolicy()
	assert_that( policy, verifiably_provides( interfaces.IMeetingPolicy ) )

	policy = _ModeratedMeetingMessagePostPolicy(moderation_state=_ModeratedMeetingState())
	assert_that( policy, verifiably_provides( interfaces.IMeetingPolicy ) )

def test_post_on_bad_channel():
	class O(object):
		channel = "Not A Good Channel"

	assert_that( _MeetingMessagePostPolicy().post_message( O ),
				 is_false() )

	assert_that( _ModeratedMeetingMessagePostPolicy(moderation_state=_ModeratedMeetingState()).post_message( O ),
				 is_false() )
